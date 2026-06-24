"""
CLI entry point for the demo.

    python src/run.py --ticket 1
    python src/run.py --message "mi envío a Perú no llegó, van 4 días"
    python src/run.py --chat                # interactive, multi-turn (the agent remembers)

It prints, in order:
  1. the customer's message,
  2. (Stage 1) the agent's tool calls + gathered facts  [shown by AgentExecutor verbose],
  3. (Stage 2) the structured AUDIT record  — the compliance log,
  4. the CUSTOMER REPLY in the customer's language.

In --chat mode the conversation is kept across turns, so the customer can reveal details
gradually (e.g. mention "Peru" first, then the recipient's name) and the agent connects them.
"""

import argparse
import json
import os
import re
import warnings
from pathlib import Path

# Quiet, clean startup for the demo. The embedding model is already cached locally, so we skip
# the Hugging Face Hub network check (removes the "unauthenticated requests" warning) and hide
# the model-loading progress bar. Must run BEFORE importing agent (which loads the model).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
warnings.filterwarnings("ignore")

from agent import resolve_ticket
from langchain_core.messages import AIMessage, HumanMessage

_TICKETS_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_tickets.md"


def _load_sample(n: int) -> str:
    """Pull the blockquote body of 'Ticket N' out of sample_tickets.md."""
    text = _TICKETS_FILE.read_text(encoding="utf-8")
    blocks = re.split(r"\*\*Ticket (\d+)", text)
    # blocks = [preamble, "1", body1, "2", body2, ...]
    for i in range(1, len(blocks), 2):
        if int(blocks[i]) == n:
            quoted = re.findall(r"^> (.*)$", blocks[i + 1], flags=re.MULTILINE)
            return " ".join(line.strip() for line in quoted).strip()
    raise SystemExit(f"No sample ticket #{n} found (try 1–5).")


def _rule(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _print_audit_and_reply(audit) -> None:
    """Print the Stage 2 audit record and the customer-facing reply."""
    _rule("STAGE 2 — AUDIT RECORD (the compliance log)")
    print(json.dumps(audit.model_dump(), indent=2, ensure_ascii=False))
    _rule("CUSTOMER REPLY  (escalated to a human)" if audit.escalate else "CUSTOMER REPLY")
    print(audit.customer_message)
    print()


def _run_once(message: str, quiet: bool) -> None:
    """One-shot resolution (no memory) — used by --ticket and --message."""
    _rule("CUSTOMER MESSAGE")
    print(message)
    _rule("STAGE 1 — gathering facts (agent + tools)")
    audit = resolve_ticket(message, verbose=not quiet)["audit"]
    _print_audit_and_reply(audit)


def _run_chat(quiet: bool) -> None:
    """Interactive, multi-turn chat. The agent remembers the conversation across turns."""
    print("\nChat mode — type the customer's messages (any language).")
    print("The agent remembers the conversation. Type 'salir', 'exit', or Ctrl-D to quit.\n")
    history: list = []
    while True:
        try:
            message = input("Cliente> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in {"salir", "exit", "quit"}:
            break
        _rule("STAGE 1 — gathering facts (agent + tools)")
        audit = resolve_ticket(message, history=history, verbose=not quiet)["audit"]
        _print_audit_and_reply(audit)
        # Remember this turn so the next message has the full conversation as context.
        history.append(HumanMessage(content=message))
        history.append(AIMessage(content=audit.customer_message))


def main() -> None:
    ap = argparse.ArgumentParser(description="Global66 transfer-complaint agent demo")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ticket", type=int, help="Run a built-in sample ticket (1–5).")
    g.add_argument("--message", type=str, help="Run your own customer message (any language).")
    g.add_argument("--chat", action="store_true", help="Interactive multi-turn chat (with memory).")
    ap.add_argument("--quiet", action="store_true", help="Hide the Stage 1 tool trace.")
    args = ap.parse_args()

    if args.chat:
        _run_chat(args.quiet)
    else:
        message = _load_sample(args.ticket) if args.ticket else args.message
        _run_once(message, args.quiet)


if __name__ == "__main__":
    main()
