# PayPilot — Friction Log

Judge note: this log documents real problems hit while building PayPilot and
how each was solved. Entries are dated and describe what actually happened.

---

## 1. Hackathon AI policy: verified CLEAR, disclosure required (2026-10-20)

**Friction:** The task required verifying the AI policy before building —
an AI-written submission to a hackathon that bans AI would be disqualifying.

**Investigation:** Read the full Official Rules at
`https://paypalaihackathon.devpost.com/rules` (sections 4, 6, 7). There is
**no ban on AI-assisted development**. Section 7 explicitly permits
contracting "technical assistance" provided the submission is the entrant's
work product. The submission form itself requires a "Tools" field:
*"identify which tools (model or AI service) were used and explain how the
tools were used in your project."*

**Solution:** Build proceeded with full disclosure: `README.md` and
`DEVPOST_SUBMISSION_DRAFT.md` document that Muse (Anthropic) assisted with
code/docs and that an optional LLM brain parses utterances. Nothing AI-made
is presented as human work. Eligibility also confirmed: India is not on the
excluded-residents list (Brazil, Quebec, Russia, sanctioned countries).

---

## 2. No PayPal sandbox credentials available (2026-10-20)

**Friction:** The entrant has no PayPal account on record and his Gmail
session is signed out, so the PayPal Developer signup's email-verification
click cannot be completed by automation. Real sandbox API calls were
impossible during the build.

**Solution:** Built a `PaymentAdapter` interface with two backends:
`MockAdapter` (deterministic, zero credentials — every agent code path runs
and is unit-tested) and `PayPalSandboxAdapter` (real Invoices v2 + Orders v2
REST calls, stdlib-only, written directly against the official docs).
All 12 unit tests run against the mock; the sandbox adapter's live paths are
clearly marked UNTESTED pending credentials. Every demo reply is badged
"DEMO — not real PayPal data". The single pending his-step (PayPal Developer
signup email verification) is recorded in `PENDING_STEPS.md`.

---

## 3. Description extraction produced garbled summaries (2026-10-20)

**Friction:** The first version of the rule-based NL parser left residue like
`"PayPal painting house cost of to % tax % discount. expires in days"` as the
invoice description — ugly and unprofessional in the demo.

**Investigation:** Two bugs: (a) the expiry regex ran *after* the money regex
had already stripped the digits it needed (`expires in  days` never matched),
and (b) filler words ("paypal", "cost", "to", "payment") and stray `%` signs
were never removed.

**Solution:** Reordered extraction (expiry before money), added the filler
words to the stop-list, stripped stray `%` tokens, and trimmed trailing
fragments. PayPal's own blog example now parses to description
`"painting house"`, amount 450, tax 8%, discount 5%, expiry 10 days.

---

## 4. stdlib-only networking to dodge runtime proxy issues (2026-10-20)

**Friction:** This runtime ships a bracketed IPv6 token (`[::1]`) in
`no_proxy`, which crashes `httpx` at client-construction time (learned on the
TripPilot build).

**Solution:** PayPilot uses only `urllib` from the standard library — no
`httpx`, no `requests`, no `fastapi`. Zero dependencies, zero proxy
surprises, and judges can run it with a bare Python 3.10+ install.
