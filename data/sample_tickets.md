# Sample customer tickets

These map to records in `transfers.json`. Each is a realistic message in the wild — vague,
emotional, multilingual — i.e. exactly the unstructured input that justifies an LLM.

Run any of them with: `python src/run.py --ticket <N>`

---

**Ticket 1 — Spanish, compliance hold (G66-2041)**
> Hola, mandé plata a mi mamá Rosa en Perú hace dos días y todavía no le llega. Normalmente
> llega rapidísimo. ¿Qué está pasando? Me preocupa que se haya perdido.

*Expected behavior:* find G66-2041 → status = compliance_hold → policy on AML holds → reassure,
explain the review, give the timeline, **escalate = true** (compliance).

---

**Ticket 2 — English, perceived failure but actually completed (G66-2042)**
> Hi, I sent money to my own US account yesterday and the app says completed but I don't see it
> in my bank. Did it fail? Should I send it again??

*Expected behavior:* find G66-2042 → status = completed → policy on bank posting times →
reassure, tell them NOT to resend, give the post window. **escalate = false.**

---

**Ticket 3 — Spanish, genuine failure, refund (G66-2043)**
> Buenas, mi transferencia a Maria en Venezuela no llegó y ya pasaron días. La cuenta que puse
> creo que estaba mal. ¿Pierdo mi plata?

*Expected behavior:* find G66-2043 → status = failed_invalid_account → refund policy → explain
the refund, amount, timeline, how to retry with a correct account. **escalate = false** (standard
refund), but flag for refund processing.

---

**Ticket 4 — Portuguese, normal delay, no problem (G66-2044)**
> Oi, enviei dinheiro para o Tomás na Bolívia hoje de manhã e ainda não chegou. Está com
> problema?

*Expected behavior:* find G66-2044 → status = in_progress, within window → transfer-times policy
→ reassure, give expected delivery date. **escalate = false.**

---

**Ticket 5 — English, recipient KYC hold (G66-2055)**
> My friend Daniela in Colombia says she got a message asking for her ID to receive the money I
> sent. Is this a scam? I'm worried.

*Expected behavior:* find G66-2055 → status = on_hold_kyc → KYC policy → confirm it's legitimate,
explain what the recipient must do, reassure about safety. **escalate = false** (standard KYC),
but emphasize anti-fraud guidance.
