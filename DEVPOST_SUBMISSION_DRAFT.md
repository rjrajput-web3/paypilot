# Devpost Submission Draft — PayPilot (FILLED — ready to paste)

> Fill into https://paypalaihackathon.devpost.com/ → "Enter a Submission".
> Deadline: Nov 13, 2026, 01:30 IST (Nov 12, 20:00 UTC).

## Project title
PayPilot — talk to PayPal in plain English

## Tagline
An AI agent that does real PayPal commerce work via natural language:
invoices, payment links, reminders, and order tracking — from a chat box.

## Description
Freelancers and small businesses lose hours to billing admin: logging into
dashboards, filling invoice forms, computing tax and discounts, chasing late
payments. **PayPilot** removes all of that. You talk to it in plain English —
*"Create a PayPal invoice link for painting a house with a cost of $450. Add
8% tax and apply 5% discount. Make sure it expires in 10 days"* — and the
agent plans and executes the work against PayPal's real APIs: it drafts the
invoice (totals computed: $461.70), returns a shareable pay link, and on
*"send it"* emails it to the client via PayPal.

**What it does**
- Natural-language invoicing: amount, tax %, discount %, expiry, recipient
  email — all parsed from one sentence (PayPal Invoices API v2)
- Send, status-check, payment reminders, and cancellation of invoices
- Instant shareable payment links (PayPal Orders API v2, CAPTURE intent)
- Order/payment-link tracking
- Agentic session memory: "send it" / "remind the client" / "what's the
  status of that invoice?" resolve without repeating IDs
- Slot-filling: missing email or amount → the agent asks and resumes
- Honest mode badge on every reply (demo backend vs real sandbox)

**Architecture**
`NL parser (deterministic rules + optional LLM brain)` → `agent orchestrator
(plans, memory, slot-filling)` → `PaymentAdapter` → `PayPalSandboxAdapter`
(real Invoices v2 + Orders v2 REST) or `MockAdapter` (deterministic demo).
Zero dependencies — Python 3.10+ standard library only, so judges can run it
with one command.

**Try it**
```bash
git clone https://github.com/rjrajput-web3/paypilot && cd paypilot
python3 -m paypilot.cli demo        # scripted end-to-end demo
PORT=8080 python3 -m paypilot.webapp   # chat UI at http://127.0.0.1:8080
python3 -m unittest discover -s tests  # 12 tests
```
Set `PAYPAL_MODE=sandbox` with `PAYPAL_CLIENT_ID`/`PAYPAL_CLIENT_SECRET`
from a free PayPal Developer sandbox app to run against real sandbox APIs.

## Tools used (AI disclosure — required field)
- **Muse (Anthropic)** — AI coding assistant used transparently to help write
  the Python code, unit tests, and documentation in this repository. All code
  was reviewed, executed, and tested by the entrant; the project is the
  entrant's original work.
- **Optional LLM brain** — PayPilot can optionally parse user utterances with
  any OpenAI-compatible chat model (via `LLM_API_KEY`); it falls back to a
  built-in deterministic rule parser. The LLM is an interchangeable
  component, not the product.
- **PayPal Developer Platform** — Invoices API v2 and Orders API v2 (sandbox),
  the same APIs behind PayPal's official Agent Toolkit/MCP invoicing example.
- No AI-generated content is presented as human work anywhere in the project.

## Links
- Public repo: https://github.com/rjrajput-web3/paypilot
- Demo video (<3 min, public YouTube): [YOUTUBE_URL — kal video upload ke baad yahan paste karo]
- License: MIT (visible at repo root and in the repo About section)

## Built with
`paypal-api` `invoices-api` `orders-api` `ai-agent` `nlp` `python` `sandbox`
