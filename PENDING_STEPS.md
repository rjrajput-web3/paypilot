# PayPilot — Pending Steps to Submission

Deadline: **Nov 13, 2026, 01:30 IST** (Nov 12, 12:00 PM PT).
Status as of 2026-10-20: v1 built, tested, committed locally. Nothing here
needs a password, OTP, or credential shared with anyone — ever.

## 1. HIS STEP — PayPal Developer signup + sandbox credentials (~5 min, on his phone/PC)

Why: lets the demo run against PayPal's *real* sandbox APIs instead of the
mock backend (stronger "Technological Implementation" score).

- Go to https://developer.paypal.com/ → sign up / log in (his Gmail).
- **Email-verification click** in his Gmail inbox (this is the step automation
  cannot do — his Gmail session is signed out).
- Dashboard → Apps & Credentials → Sandbox → create app → copy **Client ID**
  and **Secret**.
- Hand the two values to the agent (paste into chat is fine for *sandbox*
  credentials — they are throwaway test keys, not his real PayPal login).
- Agent sets `PAYPAL_MODE=sandbox`, re-runs the demo, captures real sandbox
  invoice links/screenshots for the submission.

Fallback: if this never happens, the submission still works — the mock
backend demo is honest and complete. But real sandbox links are better.

## 2. AGENT STEP — push the repo to GitHub (blocked on his `gh` session)

- `gh auth status` currently shows **not logged in** — so the repo is
  committed locally only (see git log in the work dir).
- When his GitHub session is available in the automation environment:
  `gh repo create paypilot --public --source=. --push` under `rjrajput-web3`.
- Never create a new GitHub account; use his existing `rjrajput-web3` session.

## 3. AGENT+HIS STEP — demo video (<3 min, public YouTube)

- Script/shot list: `DEMO_SCRIPT.md`.
- Video pipeline note: generate the video when the pipeline is available;
  upload as **Public** to YouTube; put the link in the Devpost form.
- Re-record against the real sandbox backend if step 1 completes first.

## 4. AGENT STEP — submit on Devpost

- Paste-ready fields: `DEVPOST_SUBMISSION_DRAFT.md` (title, tagline,
  description, tools/AI disclosure, repo link, video link, setup instructions).
- Submit at https://paypalaihackathon.devpost.com/ before the deadline.
- His Devpost account is already registered for the hackathon.

## Suggested order

1 → 2 → 3 → 4. Steps 2 and 4 need only his normal logged-in sessions
(Devpost already registered; GitHub session when available).
Bundle step 1 with his other phone steps — one tap session, not a new ask.
