"""Backend-agnostic interface for everything PayPilot can do with money.

Every method returns plain dicts so the agent layer never depends on a
specific PayPal SDK. The same conversation script runs unchanged against the
MockAdapter (demo) and the PayPalSandboxAdapter (real sandbox APIs).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class PaymentAdapter(ABC):
    """Contract for PayPal-backed commerce operations."""

    name: str = "base"

    # ---- Invoices (PayPal Invoices API v2) ----
    @abstractmethod
    def create_invoice(
        self,
        *,
        description: str,
        amount: float,
        currency: str = "USD",
        recipient_email: Optional[str] = None,
        tax_pct: Optional[float] = None,
        discount_pct: Optional[float] = None,
        days_valid: Optional[int] = None,
        invoice_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a DRAFT invoice. Returns id, number, status, links, totals."""

    @abstractmethod
    def send_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Send a draft invoice to the recipient. Returns id, status, links."""

    @abstractmethod
    def list_invoices(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Dict[str, Any]:
        """List invoices, optionally filtered by status."""

    @abstractmethod
    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Fetch one invoice with line items, totals and links."""

    @abstractmethod
    def remind_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Send a payment reminder for an invoice."""

    @abstractmethod
    def cancel_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Cancel/void an invoice."""

    # ---- Orders / payment links (PayPal Orders API v2) ----
    @abstractmethod
    def create_order(
        self,
        *,
        amount: float,
        currency: str = "USD",
        description: str = "Payment",
    ) -> Dict[str, Any]:
        """Create an order (CAPTURE intent). Returns id, status, approve_url."""

    @abstractmethod
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Fetch an order's current status (track a payment link)."""


def pick_adapter() -> PaymentAdapter:
    """Choose backend from the environment.

    PAYPAL_MODE=sandbox  +  PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET set
        -> real PayPal sandbox REST APIs.
    Anything else -> deterministic MockAdapter (demo mode).
    """
    import os

    if os.environ.get("PAYPAL_MODE", "mock").lower() == "sandbox":
        from .paypal_sandbox_adapter import PayPalSandboxAdapter

        client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
        client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise RuntimeError(
                "PAYPAL_MODE=sandbox but PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET "
                "are not set. See .env.example and PENDING_STEPS.md."
            )
        return PayPalSandboxAdapter(client_id=client_id, client_secret=client_secret)
    from .mock_adapter import MockAdapter

    return MockAdapter()


def summarize_invoices(invoices: List[Dict[str, Any]]) -> str:
    lines = []
    for inv in invoices:
        lines.append(
            f"- {inv['number']} ({inv['id']}): {inv['status']} — "
            f"{inv['currency']} {inv['total']:.2f} — {inv.get('description', '')}"
        )
    return "\n".join(lines)
