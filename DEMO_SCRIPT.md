# PayPilot — Demo Video Script (<3 minutes, public YouTube)

Record the real screen (web UI at http://127.0.0.1:8080 and/or terminal).
No copyrighted music; no third-party trademarks beyond PayPal's own (fair use
in a PayPal hackathon submission). Watermark: @MysticOp07 only if posted from X;
for YouTube/Devpost use "Rohit Rajput" per the watermark rule.

## Shot list

**0:00–0:20 — Hook**
- "Freelancers lose hours to invoicing admin. PayPilot lets you bill clients
  in plain English — it's an AI agent wired directly into PayPal."
- Show the chat UI.

**0:20–1:10 — The hero flow (PayPal's own example, live)**
- Type: *"Create a PayPal invoice link for painting a house with a cost of
  $450 to client@example.com. Add 8% tax and apply 5% discount. Make sure it
  expires in 10 days."*
- Narrate: "It parsed amount, tax, discount, expiry — drafted the invoice,
  computed $461.70, and gave me a shareable pay link."
- Type *"send it"* → "Sent — the client gets the PayPal email."
- (If sandbox mode is live by recording time: show the real PayPal sandbox
  invoice link opening in a browser tab.)

**1:10–1:50 — Payment links + tracking**
- *"Create a $99 payment link for the Pro plan"* → show the checkout URL.
- *"List my invoices"* → show the list.
- *"Remind the client about the first invoice"* → reminder sent.

**1:50–2:30 — Under the hood (quick)**
- Flash the architecture: NL parser (rules + optional LLM) → agent with
  session memory → PayPal Invoices v2 + Orders v2 sandbox APIs.
- Show `python3 -m unittest discover -s tests` → "12 tests, OK".
- Show the honest mode badge: "Every reply says whether it's demo or real
  sandbox data — no fake PayPal screenshots."

**2:30–2:55 — Close**
- "PayPilot: talk, and PayPal does the paperwork. Built for the PayPal AI
  Hackathon — PayPal sandbox + AI, end to end."
- End card: repo link + "Built by Rohit Rajput".

## Recording notes
- 1080p screen capture, system audio off, voiceover in clear English.
- Keep each chat turn visible ≥4 seconds so judges can read it.
- Total must stay under 3:00 — judges aren't required to watch past that.
