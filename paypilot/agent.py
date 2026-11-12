"""PayPilot agent — the agentic orchestrator.

Conversation -> intent (nlp.parse) -> plan -> one or more adapter calls ->
natural-language answer with a visible action trace.

Agentic behaviors:
- multi-step plans (create invoice -> ask to send -> send on confirmation)
- session memory ("send it" resolves to the last draft invoice)
- slot-filling (missing email or amount -> asks, remembers the pending draft)
- honest mode badge: every answer says whether it ran in demo (mock) or
  sandbox mode, and which brain (rules vs LLM) parsed the request.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .adapter import PaymentAdapter, summarize_invoices
from .nlp import Intent, parse

HELP_TEXT = (
    "I'm PayPilot — talk to me in plain English and I'll do PayPal work for you:\n"
    "• \"Create an invoice for $450 for painting a house to client@example.com, "
    "add 8% tax and 5% discount, expires in 10 days\"\n"
    "• \"Send it\" / \"Send invoice INV-PP-0001\"\n"
    "• \"List my invoices\" / \"What's the status of INV-PP-0001?\"\n"
    "• \"Remind the client about INV-PP-0001\" / \"Cancel INV-PP-0002\"\n"
    "• \"Create a $99 payment link for the Pro plan\" / \"Track order 7PP...\""
)


class Agent:
    def __init__(self, adapter: PaymentAdapter) -> None:
        self.adapter = adapter
        self.last_invoice_id: Optional[str] = None
        self.pending_invoice: Optional[Dict[str, Any]] = None
        self.history: List[Dict[str, str]] = []

    # ---------- public ----------
    def handle(self, text: str) -> Dict[str, Any]:
        intent = parse(text)
        try:
            reply = self._dispatch(intent)
        except (KeyError, ValueError) as e:
            reply = f"I couldn't do that: {e}"
        except Exception as e:  # never crash the chat on a backend error
            reply = f"Something went wrong on the PayPal side: {e}"
        reply = f"{reply}\n\n_[mode: {self.adapter.name}" \
            f"{' · DEMO — not real PayPal data' if self.adapter.name == 'mock' else ''}" \
            f" · brain: {intent.brain}]_"
        self.history.append({"user": text, "agent": reply})
        return {"reply": reply, "intent": intent.to_dict(),
                "mode": self.adapter.name}

    # ---------- dispatch ----------
    def _resolve_invoice_id(self, intent: Intent) -> Optional[str]:
        if intent.invoice_id:
            return intent.invoice_id
        return self.last_invoice_id

    def _dispatch(self, intent: Intent) -> str:
        name = intent.name
        if name == "help":
            return HELP_TEXT
        if name == "create_invoice":
            return self._create_invoice(intent)
        if name == "send_invoice":
            return self._send_invoice(intent)
        if name == "list_invoices":
            return self._list_invoices()
        if name == "invoice_status":
            return self._invoice_status(intent)
        if name == "remind_invoice":
            return self._remind_invoice(intent)
        if name == "cancel_invoice":
            return self._cancel_invoice(intent)
        if name == "create_order":
            return self._create_order(intent)
        if name == "order_status":
            return self._order_status(intent)
        return ("I didn't catch that. " + HELP_TEXT)

    # ---------- intents ----------
    def _create_invoice(self, intent: Intent) -> str:
        if not intent.amount:
            self.pending_invoice = {"intent": intent, "missing": "amount"}
            return "How much should the invoice be for? (e.g. \"$450\")"
        if not intent.email:
            self.pending_invoice = {"intent": intent, "missing": "email"}
            return (f"Got it — {intent.description or 'services'} for "
                    f"{intent.currency} {intent.amount:.2f}. "
                    "What's the client's email address?")
        inv = self.adapter.create_invoice(
            description=intent.description or "Services",
            amount=intent.amount,
            currency=intent.currency,
            recipient_email=intent.email,
            tax_pct=intent.tax_pct,
            discount_pct=intent.discount_pct,
            days_valid=intent.days_valid,
        )
        self.last_invoice_id = inv["id"]
        self.pending_invoice = None
        bits = [f"Invoice {inv['number']} ({inv['id']}) drafted for "
                f"{inv['currency']} {inv['total']:.2f}"]
        if inv.get("discount"):
            bits.append(f"(incl. {intent.discount_pct}% discount)")
        if inv.get("tax"):
            bits.append(f"(incl. {intent.tax_pct}% tax)")
        bits.append(f"to {inv['recipient_email']}.")
        bits.append(f"\nShare link: {inv['links']['share']}")
        bits.append("\nSay \"send it\" and I'll email it to the client.")
        return " ".join(bits)

    def _send_invoice(self, intent: Intent) -> str:
        iid = self._resolve_invoice_id(intent)
        if not iid:
            return "Which invoice should I send? Give me its ID (e.g. INV-PP-0001)."
        inv = self.adapter.send_invoice(iid)
        return (f"Sent! Invoice {inv['number']} is now {inv['status']} — "
                f"the client can pay at {inv['links']['share']}")

    def _list_invoices(self) -> str:
        data = self.adapter.list_invoices(page_size=10)
        if not data["total"]:
            return "No invoices yet. Say \"create an invoice for $X to email\" to start."
        return f"Here are your invoices ({data['total']} total):\n" + \
            summarize_invoices(data["invoices"])

    def _invoice_status(self, intent: Intent) -> str:
        iid = self._resolve_invoice_id(intent)
        if not iid:
            return "Which invoice? Give me its ID (e.g. INV-PP-0001)."
        inv = self.adapter.get_invoice(iid)
        return (f"Invoice {inv['number']} ({inv['id']}): {inv['status']} — "
                f"{inv['currency']} {inv['total']:.2f} for "
                f"\"{inv['description']}\". Pay link: {inv['links']['share']}")

    def _remind_invoice(self, intent: Intent) -> str:
        iid = self._resolve_invoice_id(intent)
        if not iid:
            return "Which invoice should I remind about?"
        inv = self.adapter.remind_invoice(iid)
        n = inv.get("reminders_sent", 1)
        return (f"Reminder sent to {inv['recipient_email']} for invoice "
                f"{inv['number']} ({n} reminder{'s' if n != 1 else ''} total).")

    def _cancel_invoice(self, intent: Intent) -> str:
        iid = self._resolve_invoice_id(intent)
        if not iid:
            return "Which invoice should I cancel?"
        inv = self.adapter.cancel_invoice(iid)
        return f"Cancelled invoice {inv['number']} — it's now {inv['status']}."

    def _create_order(self, intent: Intent) -> str:
        if not intent.amount:
            return "How much should the payment link be for? (e.g. \"$99\")"
        order = self.adapter.create_order(
            amount=intent.amount,
            currency=intent.currency,
            description=intent.description or "Payment",
        )
        return (f"Payment link ready for {order['currency']} {order['amount']:.2f} "
                f"(\"{order['description']}\"):\n{order['approve_url']}\n"
                f"Order {order['id']} is {order['status']} — say "
                f"\"track order {order['id']}\" any time to check it.")

    def _order_status(self, intent: Intent) -> str:
        if not intent.order_id:
            return "Which order? Paste its order ID."
        order = self.adapter.get_order(intent.order_id)
        return (f"Order {order['id']}: {order['status']} — "
                f"{order['currency']} {order['amount']:.2f} "
                f"(\"{order['description']}\").")
