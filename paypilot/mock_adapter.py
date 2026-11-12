"""Deterministic demo backend. No network, no credentials.

Implements the same PaymentAdapter contract as the real PayPal sandbox
backend, so every agent code path is exercised honestly in demo mode.
All IDs, links and totals are clearly fake and every agent response is
badged "demo mode" — never presented as real PayPal data.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .adapter import PaymentAdapter


class MockAdapter(PaymentAdapter):
    name = "mock"

    def __init__(self) -> None:
        self._invoices: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._inv_seq = 0
        self._ord_seq = 0

    # ---------- helpers ----------
    def _new_invoice_id(self) -> str:
        self._inv_seq += 1
        return f"INV-PP-{self._inv_seq:04d}"

    def _new_order_id(self) -> str:
        self._ord_seq += 1
        return f"7PP{self._ord_seq:06d}MOCK"

    def _invoice_or_raise(self, invoice_id: str) -> Dict[str, Any]:
        inv = self._invoices.get(invoice_id) or self._invoices.get(
            invoice_id.upper()
        )
        if not inv:
            raise KeyError(f"Unknown invoice id: {invoice_id}")
        return inv

    @staticmethod
    def _totals(amount: float, tax_pct: float, discount_pct: float) -> Dict[str, float]:
        discount = round(amount * discount_pct / 100.0, 2)
        taxable = amount - discount
        tax = round(taxable * tax_pct / 100.0, 2)
        total = round(taxable + tax, 2)
        return {"subtotal": round(amount, 2), "discount": discount,
                "tax": tax, "total": total}

    # ---------- invoices ----------
    def create_invoice(self, *, description, amount, currency="USD",
                       recipient_email=None, tax_pct=None, discount_pct=None,
                       days_valid=None, invoice_number=None) -> Dict[str, Any]:
        if amount is None or amount <= 0:
            raise ValueError("Invoice amount must be positive.")
        inv_id = self._new_invoice_id()
        totals = self._totals(amount, tax_pct or 0.0, discount_pct or 0.0)
        now = datetime.now(timezone.utc)
        inv = {
            "id": inv_id,
            "number": invoice_number or f"PP-{self._inv_seq:05d}",
            "status": "DRAFT",
            "description": description or "Services",
            "currency": currency.upper(),
            "recipient_email": recipient_email,
            "tax_pct": tax_pct or 0.0,
            "discount_pct": discount_pct or 0.0,
            "created_at": now.isoformat(),
            "due_at": (now + timedelta(days=days_valid or 30)).isoformat()
            if days_valid else None,
            "links": {
                "self": f"https://api-m.sandbox.paypal.com/v2/invoicing/invoices/{inv_id}",
                # Mock share link — only valid in demo mode.
                "share": f"https://www.sandbox.paypal.com/invoice/p/mock-{inv_id.lower()}",
            },
            "reminders_sent": 0,
            **totals,
        }
        self._invoices[inv_id] = inv
        return dict(inv)

    def send_invoice(self, invoice_id: str) -> Dict[str, Any]:
        inv = self._invoice_or_raise(invoice_id)
        if inv["status"] != "DRAFT":
            raise ValueError(f"Only DRAFT invoices can be sent (is {inv['status']}).")
        if not inv.get("recipient_email"):
            raise ValueError("Recipient email is required before sending.")
        inv["status"] = "SENT"
        inv["sent_at"] = datetime.now(timezone.utc).isoformat()
        return dict(inv)

    def list_invoices(self, status=None, page=1, page_size=10) -> Dict[str, Any]:
        invs = list(self._invoices.values())
        if status:
            invs = [i for i in invs if i["status"] == status.upper()]
        start = (page - 1) * page_size
        return {
            "invoices": [dict(i) for i in invs[start:start + page_size]],
            "total": len(invs),
            "page": page,
        }

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        return dict(self._invoice_or_raise(invoice_id))

    def remind_invoice(self, invoice_id: str) -> Dict[str, Any]:
        inv = self._invoice_or_raise(invoice_id)
        if inv["status"] != "SENT":
            raise ValueError("Can only remind on SENT invoices.")
        inv["reminders_sent"] += 1
        inv["last_reminder_at"] = datetime.now(timezone.utc).isoformat()
        return dict(inv)

    def cancel_invoice(self, invoice_id: str) -> Dict[str, Any]:
        inv = self._invoice_or_raise(invoice_id)
        if inv["status"] in ("PAID", "CANCELLED"):
            raise ValueError(f"Cannot cancel an invoice in status {inv['status']}.")
        inv["status"] = "CANCELLED"
        inv["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        return dict(inv)

    # ---------- orders ----------
    def create_order(self, *, amount, currency="USD",
                     description="Payment") -> Dict[str, Any]:
        if amount is None or amount <= 0:
            raise ValueError("Order amount must be positive.")
        oid = self._new_order_id()
        order = {
            "id": oid,
            "status": "CREATED",
            "intent": "CAPTURE",
            "description": description,
            "currency": currency.upper(),
            "amount": round(amount, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            # Mock approval link — only valid in demo mode.
            "approve_url": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}",
            "links": {
                "self": f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{oid}",
                "approve": f"https://www.sandbox.paypal.com/checkoutnow?token={oid}",
            },
        }
        self._orders[oid] = order
        return dict(order)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        order = self._orders.get(order_id) or self._orders.get(order_id.upper())
        if not order:
            raise KeyError(f"Unknown order id: {order_id}")
        return dict(order)
