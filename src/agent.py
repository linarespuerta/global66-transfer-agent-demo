"""
The agent: two stages.

STAGE 1 — GATHER (a LangChain tool-calling agent)
    The agent reads the customer's message and decides which tools to call to learn the facts:
    find the transfer, read its real status, and look up the relevant policy. It does NOT decide
    the outcome here — its only job is to collect ground truth. This keeps the LLM away from
    inventing facts about people's money.

STAGE 2 — DECIDE & FORMAT (a structured-output call)
    Given the gathered facts, a single Gemini call produces a typed `ResolutionAudit`: the
    diagnosis, the action, an explicit escalate flag + reason, and the customer-facing reply in
    the customer's own language. Typed output = an auditable compliance record, by construction.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from pydantic import BaseModel, Field

import rag
import transfer_api

load_dotenv()

GATHER_MODEL = os.getenv("GATHER_MODEL", "gemini-2.5-flash")  # cheap/fast for tool use
# Stage 2 uses pro for a sharper, warmer reply. Requires billing enabled on the project
# (pro is quota=0 on the free tier). Set DECIDE_MODEL=gemini-2.5-flash to stay free-tier-only.
DECIDE_MODEL = os.getenv("DECIDE_MODEL", "gemini-2.5-pro")    # stronger for the decision


# ---------------------------------------------------------------------------
# Tools — the agent's only window into the world. Note the deliberate split:
# the first two are DETERMINISTIC lookups; the third is the RAG (AI) retrieval.
# ---------------------------------------------------------------------------
@tool
def find_transfer(query: str) -> str:
    """Find candidate transfers when the customer does NOT give a transfer ID.
    Search by recipient name, sender name, or destination country.
    Returns a list of matching transfers (with their IDs) or a no-match message."""
    hits = transfer_api.find_transfers(query)
    if not hits:
        return "No matching transfer found. Ask the customer for a transfer ID or recipient name."
    return "\n".join(transfer_api.summarize(t) for t in hits)


@tool
def get_transfer_status(transfer_id: str) -> str:
    """Get the exact, current status of one transfer by its ID (e.g. 'G66-2043').
    Use this once you know the transfer ID to read its real state. Never guess a status."""
    t = transfer_api.get_transfer(transfer_id)
    if t is None:
        return f"No transfer found with id {transfer_id}."
    return transfer_api.summarize(t)


@tool
def search_policy(question: str) -> str:
    """Search Global66's policy knowledge base (transfer times, compliance/KYC holds, failed
    transfers, refunds). Use this for any question about rules, timelines, escalation, or what
    the customer is entitled to. Returns grounded policy passages with their source."""
    return rag.search_policy(question)


TOOLS = [find_transfer, get_transfer_status, search_policy]


# ---------------------------------------------------------------------------
# Stage 2 output schema — the auditable record.
# ---------------------------------------------------------------------------
class ResolutionAudit(BaseModel):
    """A structured, logged record of how the agent resolved one complaint."""

    language: str = Field(description="The customer's language, e.g. 'es', 'en', 'pt'.")
    transfer_id: str | None = Field(description="The transfer ID involved, or null if not found.")
    category: str = Field(
        description="One of: normal_delay, completed_bank_pending, compliance_hold, "
        "kyc_hold, failed_refund, not_found."
    )
    diagnosis: str = Field(description="One-sentence internal explanation of what is actually going on.")
    recommended_action: str = Field(description="What Global66 will do or what the customer should do.")
    escalate: bool = Field(description="True only when a human team (e.g. Compliance) must take over.")
    escalation_reason: str | None = Field(description="Why we escalate, or null if escalate is false.")
    customer_message: str = Field(
        description="The reply to send the customer, written in THEIR language, warm, clear, "
        "and grounded only in the gathered facts and policy."
    )


_GATHER_SYSTEM = """You are a support investigation agent for Global66, a cross-border payments
company. A customer is worried about a transfer. Your ONLY job in this step is to gather the facts
— do not resolve the case or write a reply yet.

Steps:
1. If you don't have a transfer ID, call find_transfer using the recipient name / country.
2. Once you have an ID, call get_transfer_status to read its REAL current state. Never assume.
3. Call search_policy to retrieve the policy relevant to that state (delivery times, holds,
   failures, refunds, escalation rules).

Then output a short plain-text FACTS summary containing: the transfer id and its exact state, and
the key policy points that apply (including whether this state requires escalation). Do not write
a customer message."""

_DECIDE_SYSTEM = """You are the resolution engine for Global66 support. Given the customer's
original message and a FACTS summary gathered from the systems and policy, produce a structured
resolution.

Rules:
- Ground everything ONLY in the provided facts and policy. Never invent amounts, dates, or status.
- Copy identifiers (especially the transfer ID, e.g. "G66-2041") EXACTLY as they appear in the
  facts — no added spaces, characters, or reformatting — in both `transfer_id` and the message.
- Detect the customer's language and write `customer_message` in that language. Be warm, concise,
  and reassuring; lead with the money being safe when that is true.
- Set escalate=true ONLY when policy says a human team must take over (e.g. an AML compliance
  hold). For a routine KYC hold, normal delay, bank-posting wait, or standard failure+refund,
  escalate=false.
- For compliance (AML) holds, never tell the customer their transaction was 'flagged as
  suspicious'; describe it as a routine security review, per policy.
- Always give the customer a concrete next step or timeline."""


def resolve_ticket(message: str, history: list | None = None, verbose: bool = True) -> dict:
    """Run both stages and return {'facts': ..., 'audit': ResolutionAudit}.

    `history` is an optional list of prior LangChain messages (Human/AI). When provided, the
    agent treats this as a continuing conversation — e.g. the customer first says "my transfer
    to Peru is late" and only later gives the name "Rosa", and the agent connects the two.
    """
    history = history or []

    # --- Stage 1: gather ---
    gather_llm = ChatGoogleGenerativeAI(model=GATHER_MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _GATHER_SYSTEM),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(gather_llm, TOOLS, prompt)
    executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=verbose)
    facts = executor.invoke({"input": message, "chat_history": history})["output"]
    if isinstance(facts, list):  # thinking-enabled models return a list of content blocks
        # Keep EVERY block's text: dict blocks expose it under "text", but some blocks
        # arrive as bare strings. Dropping either one can lose the status or the
        # escalation note, which makes Stage 2 hallucinate — so flatten all of them.
        parts = [b.get("text", "") if isinstance(b, dict) else str(b) for b in facts]
        facts = " ".join(p for p in parts if p).strip()

    # --- Stage 2: decide & format into the auditable record ---
    decide_llm = ChatGoogleGenerativeAI(model=DECIDE_MODEL, temperature=0).with_structured_output(
        ResolutionAudit
    )
    audit = decide_llm.invoke(
        [
            SystemMessage(content=_DECIDE_SYSTEM),
            *history,  # prior turns, so follow-up questions stay coherent
            HumanMessage(
                content=f"CUSTOMER MESSAGE:\n{message}\n\nGATHERED FACTS:\n{facts}"
            ),
        ]
    )

    # The transfer ID is known exactly — don't trust the LLM to echo it cleanly. It
    # occasionally inserts a stray space (e.g. "G66-20 41"). Strip whitespace from the
    # id and repair any spaced-out occurrences in the customer reply, deterministically.
    if audit.transfer_id:
        canonical = re.sub(r"\s+", "", audit.transfer_id)
        audit.transfer_id = canonical
        tolerant = re.compile(r"\s*".join(re.escape(c) for c in canonical))
        audit.customer_message = tolerant.sub(canonical, audit.customer_message)

    return {"facts": facts, "audit": audit}
