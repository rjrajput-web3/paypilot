"""PayPilot — a natural-language AI agent for PayPal commerce.

Talk in plain English; PayPilot plans and executes real PayPal work
(invoices, payment links, order tracking) through a pluggable backend.

Two backends implement the same interface (`PaymentAdapter`):
- `MockAdapter`      — deterministic demo backend, zero credentials needed.
- `PayPalSandboxAdapter` — real PayPal REST APIs (Invoices v2, Orders v2)
  against the PayPal sandbox. Needs PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET.
"""

__version__ = "0.1.0"
__all__ = ["agent", "nlp", "adapter", "mock_adapter", "paypal_sandbox_adapter"]
