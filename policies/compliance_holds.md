# Policy: Compliance holds (AML) and recipient KYC holds

Some transfers are paused for regulatory reasons. These are legally required and must be handled
carefully. **Never tell a customer a specific transaction was flagged as suspicious** — explain it
as a routine security/verification step.

## AML review hold (sender side) — state: `compliance_hold`

- Triggered when a transfer falls outside the customer's normal pattern (amount, frequency,
  destination) or matches a monitoring rule.
- The funds are safe and held, not lost.
- Standard review takes **up to 1 business day**. The customer does not need to do anything unless
  we contact them to confirm details.
- **This outcome must be escalated to the Compliance team.** The agent must not release, cancel,
  or promise a release date beyond the standard window.
- Customer message: reassure that the money is safe, explain it's a routine security review, give
  the up-to-1-business-day expectation, and say the team will reach out if anything is needed.

## Recipient KYC hold — state: `on_hold_kyc`

- The **recipient** must verify their identity before funds are released. This is standard for
  first-time or higher-value receipts.
- It is **legitimate, not a scam** — an important reassurance, since customers often fear fraud.
- The recipient completes verification in the app or via the link sent to them. Funds release
  shortly after verification is approved.
- Does not require escalation, but the agent should give clear anti-fraud guidance: Global66 will
  only ask the recipient to verify identity in the official app — never ask for passwords, full
  card numbers, or payment to "release" funds.
