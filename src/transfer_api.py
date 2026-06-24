"""
Deterministic "transfer status API" — DELIBERATELY no AI here.

This is the half of the system that should NOT be an LLM. Looking up a transfer by ID or by
recipient is exact, structured work: plain Python is faster, cheaper, and 100% reliable. Putting
an LLM here would be the classic junior mistake. The agent (agent.py) *calls* these functions as
tools — it never guesses a transfer's status itself.

In production these functions would call Global66's real backoffice / partner APIs. The interface
the agent sees would not change.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "transfers.json"


def _load() -> list[dict]:
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_transfer(transfer_id: str) -> dict | None:
    """Exact lookup by transfer ID (e.g. 'G66-2043'). Returns the record or None."""
    transfer_id = transfer_id.strip().upper()
    for t in _load():
        if t["transfer_id"].upper() == transfer_id:
            return t
    return None


def find_transfers(query: str) -> list[dict]:
    """
    Fuzzy-ish search for when the customer doesn't give an ID. Matches the query against
    recipient name, sender name, and destination country (case-insensitive substring).
    Pure string matching — still deterministic, no AI.
    """
    q = query.strip().lower()
    hits = []
    for t in _load():
        haystack = " ".join(
            [t["recipient_name"], t["sender_name"], t["destination_country"]]
        ).lower()
        if any(word in haystack for word in q.split() if len(word) > 2):
            hits.append(t)
    return hits


def summarize(transfer: dict) -> str:
    """Render a transfer record as a compact, readable string for the agent to reason over."""
    return (
        f"transfer_id={transfer['transfer_id']} | "
        f"{transfer['sender_name']} → {transfer['recipient_name']} ({transfer['destination_country']}) | "
        f"corridor={transfer['corridor']} | "
        f"sent={transfer['amount_sent']} {transfer['currency_sent']} | "
        f"STATE={transfer['state']} ({transfer['state_detail']}) | "
        f"created={transfer['created_at']} | expected={transfer['expected_delivery']} | "
        f"last_updated={transfer['last_updated']}"
    )
