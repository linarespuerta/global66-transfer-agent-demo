# Global66 — Cross-Border Transfer Complaint Agent (demo)

**▶️ Demo video (2 min): https://youtu.be/C-TS09iHtnk**

A LangChain + Gemini agent that resolves a customer complaint about a stuck or failed
international transfer, **end to end**: it identifies the transfer, checks its live status,
looks up the relevant policy via RAG, decides what to do, replies in the customer's language,
and escalates to compliance only when it should — writing an **auditable record** of every
decision.

Built by Pablo Linares as a working sample for the Global66 **AI Specialist** role.

---

## The one idea this demo is built to prove

> **Knowing *when* to use AI vs. deterministic code is the senior skill — not "calling an LLM".**

- Looking up a transfer's status is **deterministic** → plain Python (`transfer_api.py`). An LLM
  here would be slower, more expensive, and less reliable.
- Understanding a messy, multilingual customer message and grounding a fair answer in policy is
  **unstructured** → that's exactly where an LLM + RAG belongs (`agent.py`, `rag.py`).

The architecture *shows the boundary*. That's the story.

---

## Architecture

```
 customer message (any language)
          │
          ▼
 ┌─────────────────────────────┐     TOOLS (the agent decides when to call each)
 │  STAGE 1 — Gather (agent)    │     ┌───────────────────────────────────────────┐
 │  LangChain tool-calling      │────▶│ find_transfer()      deterministic lookup  │
 │  agent w/ Gemini             │     │ get_transfer_status() deterministic lookup │
 │  Goal: collect the facts     │────▶│ search_policy()       RAG over policy docs │
 └─────────────────────────────┘     └───────────────────────────────────────────┘
          │  (facts summary)
          ▼
 ┌─────────────────────────────┐
 │  STAGE 2 — Decide & format   │   with_structured_output(ResolutionAudit)
 │  Gemini → structured JSON    │   → auditable compliance record
 └─────────────────────────────┘   → customer_message in the customer's language
          │
          ▼
   { customer_message , audit record }
```

Two stages on purpose:
1. **Gather** — the agent uses tools to find the truth (no improvising about money).
2. **Decide & format** — a single structured call turns the facts into (a) a customer reply and
   (b) a structured **audit log** — because in fintech *every automated decision must be logged*.

---

## What's in here

| Path | What it is |
|------|-----------|
| `src/transfer_api.py` | **Deterministic** mock "transfer status API" — plain Python, no AI |
| `src/rag.py` | Builds a FAISS vector store over the policy docs and retrieves relevant passages |
| `src/agent.py` | The LangChain agent (Stage 1) + the structured decision step (Stage 2) |
| `src/run.py` | CLI: feed it a ticket, watch it resolve |
| `policies/*.md` | The **RAG knowledge base** — unstructured policy docs (this is what RAG reads) |
| `data/transfers.json` | Mock transfer records the deterministic API serves |
| `data/sample_tickets.md` | Realistic customer messages (ES / EN / PT) to demo with |

---

## Run it

```bash
cd 06_applications/Global66/transfer_agent_demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your GOOGLE_API_KEY into .env (free, from AI Studio)

# resolve one of the built-in sample tickets (by number)
python src/run.py --ticket 1

# or pass your own complaint, in any language
python src/run.py --message "mi envío a mi mamá en Perú no ha llegado, van 4 días"

# or hold a real, multi-turn conversation — the agent remembers across turns, so the
# customer can reveal details gradually (greet first, then "my money is missing", then the name)
python src/run.py --chat
```

First run downloads a small local embedding model (~90 MB, free, no API key) to build the
vector store. Subsequent runs are instant.

---

## Why these choices (the "senior judgment" talking points)

- **Deterministic status lookup, AI only for the messy parts.** See above — this is the headline.
- **RAG, not fine-tuning, not prompt-stuffing.** Policies change weekly at a fintech; RAG means
  you update a markdown file, not a model. The agent's answers are *grounded* in retrieved policy,
  not invented.
- **Structured audit output.** `ResolutionAudit` is a typed schema. Every resolution is logged
  with the transfer ID, diagnosis, action, and an explicit `escalate` flag + reason — defensible
  to a compliance/regulatory review.
- **Escalation is a first-class outcome.** The agent is built to *stop and hand off* on compliance
  holds and genuine failures, not to paper over them. Knowing when **not** to auto-resolve is the
  point.
- **Cost-aware by design.** Stage 1 can run on a cheap/fast model (Haiku) and only Stage 2 needs
  the stronger model — the JD explicitly asks to "optimize agent precision and cost efficiency".

---

## Scope honesty (say this out loud in the interview)

This is a **demo**: mock data, a local vector store, no real Global66 systems. In production the
`transfer_api` tools become real backoffice/partner-API calls, the policy docs come from the real
knowledge base, and the audit records stream to a logging/observability stack. The *architecture*
— deterministic tools + RAG + structured audit + human escalation — is the part that transfers.
