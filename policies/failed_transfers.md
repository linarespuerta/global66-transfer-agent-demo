# Policy: Failed transfers

A transfer can fail when the receiving bank rejects it. The money is **not lost** — it is
returned and refunded to the sender.

## Common failure reasons

- `failed_invalid_account` — recipient account number is wrong, closed, or not valid for the
  receiving bank.
- `failed_name_mismatch` — recipient name does not match the account holder.
- `failed_bank_rejected` — the receiving bank declined for its own reasons.

## What happens on a failure

1. The receiving bank returns the funds to Global66.
2. Global66 **refunds the sender automatically** — see the refunds policy for amount and timeline.
3. The customer can create a new transfer with corrected recipient details.

## What to tell the customer

- Reassure first: the money is safe and will be refunded; it was not lost.
- Explain the specific reason in plain language (e.g. the destination account was not valid).
- Point them to the refund timeline.
- Invite them to retry with corrected details, and suggest double-checking the account number and
  that the recipient name matches the account exactly.
- A standard failure + refund does **not** require escalation. Escalate only if the customer
  reports they already received a refund for a different transfer that also failed, or if the same
  transfer failed repeatedly.
