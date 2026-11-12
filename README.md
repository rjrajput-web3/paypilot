# 💸 PayPilot — talk to PayPal in plain English

**PayPal AI Hackathon entry.** An AI agent that does real PayPal commerce work
via natural language: create invoices with tax/discount/expiry, send them,
track status, send payment reminders, cancel invoices, and generate shareable
payment links — all from a chat box.

> *"Create a PayPal invoice link for painting a house with a cost of $450.
> Add 8% tax and apply 5% discount. Make sure it expires in 10 days."*
> → PayPilot drafts the invoice, computes totals ($461.70), and returns a
> shareable pay link. Say **"send it"** and it's emailed to the client.

## ⚡ 30-second quickstart (zero dependencies — Python 3.10+ stdlib only)

```bash
python3 -m paypilot.cli demo        # scripted end-to-end demo in your terminal
python3 -m paypilot.cli chat       # interactive chat
PORT=8080 python3 -m paypilot.webapp   # web UI -> http://127.0.0.1:8080
python3 -m unittest discover -s tests  # 12 tests, all green
```

## 🧠 Architecture

```
  you type English
        │
        ▼
  ┌──────────┐   intent JSON    ┌──────────┐   tool calls   ┌──────────────────┐
  │ nlp.parse │ ──────────────► │ agent.py │ ──────────────► │ PaymentAdapter   │
  │ rules  ◄──┤  (LLM optional) │ (plans,   │                │  ├─ MockAdapter   │
  │ LLM    ◄──┤                 │  memory,   │                │  └─ PayPalSandbox │
  └──────────┘                 │  slots)    │                │     Adapter (REST) │
                               └──────────┘                └──────────────────┘
```

**Why it's agentic, not a thin wrapper:**
- One utterance fans out into a multi-step plan (parse → draft invoice → ask
  to send → send on confirmation), not a single API call.
- **Session memory:** "send it", "what's the status of that invoice?", and
  "remind the client" resolve against the last invoice without repeating IDs.
- **Slot-filling:** missing email or amount → the agent asks, remembers, and
  resumes the pending draft.
- **Two brains:** an optional LLM parser (any OpenAI-compatible endpoint via
  `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL`) with a deterministic rule-based
  parser as guaranteed fallback. Every reply states which brain parsed it.
- **Honest mode badge:** every reply says whether it ran against the demo
  backend or the real PayPal sandbox.

## 💳 PayPal APIs used (official, sandbox-first)

| Operation | PayPal REST endpoint |
|---|---|
| OAuth | `POST /v1/oauth2/token` (client_credentials) |
| Create draft invoice | `POST /v2/invoicing/invoices` (line-item tax + discount) |
| Send / remind / cancel | `POST /v2/invoicing/invoices/{id}/send|remind|cancel` |
| List / get invoice | `GET /v2/invoicing/invoices[/{id}]` |
| Payment link | `POST /v2/checkout/orders` (CAPTURE intent → `approve` URL) |
| Track order | `GET /v2/checkout/orders/{id}` |

Set `PAYPAL_MODE=sandbox` plus `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`
(from a free [PayPal Developer](https://developer.paypal.com/) sandbox app)
to run against real sandbox APIs. Default is the deterministic mock backend —
every agent code path is exercised identically, and demo responses are always
badged "DEMO — not real PayPal data".

## 🤖 AI disclosure (for the Devpost "Tools" field)

AI assistance was used transparently in building this project:
- **Muse (Anthropic)** — AI coding assistant: helped write the Python code,
  tests, and documentation in this repo. All code was reviewed, run, and
  tested by the entrant.
- **Optional LLM brain** — PayPilot can optionally parse user utterances with
  any OpenAI-compatible chat model (`LLM_API_KEY`), falling back to the
  built-in deterministic parser. The LLM is an interchangeable component, not
  the product.
- No AI-generated content is presented as human work anywhere in the project
  or demo.

The hackathon's Official Rules contain **no ban on AI-assisted development**;
the submission form explicitly asks entrants to identify the AI tools used,
which is done above and in `DEVPOST_SUBMISSION_DRAFT.md`.

## 🗺️ Judging-criteria mapping

| Criterion | How PayPilot addresses it |
|---|---|
| Technological Implementation | Real PayPal Invoices v2 + Orders v2 integration, MCP-style tool architecture, dual backends, optional LLM brain |
| Design | Complete chat product (web UI + CLI), session memory, slot-filling, honest mode badges |
| Potential Impact | Freelancers/small businesses bill clients conversationally — PayPal's own MCP invoicing example, productized |
| Innovation | NL → multi-step PayPal commerce plans with agentic memory, zero-dependency runnable |
| Presentation | Scripted terminal demo + web UI demo + <3 min video plan in `DEMO_SCRIPT.md` |

## 📁 Layout

```
paypilot/            agent, NL parser, adapter interface, mock + sandbox backends, web UI, CLI
tests/               12 unit tests (mock backend, parser, agent flows)
static/index.html    chat web UI
demo/                demo transcripts
.env.example         env vars for sandbox mode + optional LLM brain
PENDING_STEPS.md     the 4 remaining steps to submission (incl. his-step: PayPal Developer signup)
DEMO_SCRIPT.md       <3 min video shot list
DEVPOST_SUBMISSION_DRAFT.md   paste-ready Devpost fields
FRICTION_LOG.md      real build problems + solutions
```

## 📄 License

MIT — see `LICENSE`.
