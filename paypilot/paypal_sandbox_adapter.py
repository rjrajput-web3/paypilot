"""Real PayPal sandbox backend — PayPal REST APIs, stdlib only.

Endpoints used (all under https://api-m.sandbox.paypal.com):
- POST /v1/oauth2/token                       OAuth2 client_credentials
- POST /v2/invoicing/invoices                 create draft invoice
- POST /v2/invoicing/invoices/{id}/send       send invoice
- GET  /v2/invoicing/invoices                 list invoices
- GET  /v2/invoicing/invoices/{id}            get invoice
- POST /v2/invoicing/invoices/{id}/remind     payment reminder
- POST /v2/invoicing/invoices/{id}/cancel     cancel invoice
- POST /v2/checkout/orders                    create order (CAPTURE)
- GET  /v2/checkout/orders/{id}               get order

Reference: PayPal Developer docs — Invoices API v2 and Orders API v2,
and the PayPal Agent Toolkit / MCP server docs (same underlying APIs).

HONESTY NOTE: this adapter is written directly against the official docs
but its live code paths are UNTESTED until real sandbox credentials exist
(see PENDING_STEPS.md). The MockAdapter covers all agent logic in tests.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .adapter import PaymentAdapter

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


class PayPalError(RuntimeError):
    pass


class PayPalSandboxAdapter(PaymentAdapter):
    name = "paypal-sandbox"

    def __init__(self, *, client_id: str, client_secret: str,
                 base_url: str = SANDBOX_BASE) -> None:
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required.")
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._token_expires_at = 0.0

    # ---------- low-level HTTP ----------
    def _request(self, method: str, path: str,
                 body: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, str]] = None,
                 idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        token = self._access_token()
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode() or "{}"
                return json.loads(raw)
        except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
            detail = e.read().decode()[:500]
            raise PayPalError(f"PayPal {method} {path} -> HTTP {e.code}: {detail}")

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        creds = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
        req = urllib.request.Request(
            self.base_url + "/v1/oauth2/token",
            data=body,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
            raise PayPalError(f"OAuth token request failed: HTTP {e.code}")
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 300))
        return self._token

    # ---------- response shaping ----------
    @staticmethod
    def _shape_invoice(inv: Dict[str, Any]) -> Dict[str, Any]:
        detail = inv.get("detail", {}) or {}
        amount = inv.get("amount", {}) or {}
        links = {l.get("rel", ""): l.get("href", "") for l in inv.get("links", [])}
        share = next(
            (href for rel, href in links.items() if "view" in rel or "payer" in rel),
            links.get("self", ""),
        )
        return {
            "id": inv.get("id", ""),
            "number": detail.get("invoice_number", ""),
            "status": inv.get("status", ""),
            "description": (inv.get("items") or [{}])[0].get("name", ""),
            "currency": detail.get("currency_code", "USD"),
            "recipient_email": ((inv.get("primary_recipients") or [{}])[0]
                                .get("billing_info", {}) or {}).get("email_address"),
            "total": float((amount.get("value") or "0").replace(",", "") or 0.0),
            "links": {"self": links.get("self", ""), "share": share},
            "raw": inv,
        }

    @staticmethod
    def _shape_order(order: Dict[str, Any]) -> Dict[str, Any]:
        pu = (order.get("purchase_units") or [{}])[0]
        amt = pu.get("amount", {}) or {}
        links = {l.get("rel", ""): l.get("href", "") for l in order.get("links", [])}
        return {
            "id": order.get("id", ""),
            "status": order.get("status", ""),
            "intent": order.get("intent", ""),
            "description": pu.get("description", ""),
            "currency": amt.get("currency_code", "USD"),
            "amount": float((amt.get("value") or "0").replace(",", "") or 0.0),
            "approve_url": links.get("approve", ""),
            "links": links,
            "raw": order,
        }

    # ---------- invoices ----------
    def create_invoice(self, *, description, amount, currency="USD",
                       recipient_email=None, tax_pct=None, discount_pct=None,
                       days_valid=None, invoice_number=None) -> Dict[str, Any]:
        if amount is None or amount <= 0:
            raise ValueError("Invoice amount must be positive.")
        if not recipient_email:
            raise ValueError("Recipient email is required to create an invoice.")
        now = datetime.now(timezone.utc)
        item: Dict[str, Any] = {
            "name": description or "Services",
            "quantity": "1",
            "unit_amount": {"currency_code": currency.upper(),
                            "value": f"{amount:.2f}"},
        }
        if discount_pct:
            item["discount"] = {"percent": f"{discount_pct}"}
        if tax_pct:
            item["tax"] = {"name": "Tax", "percent": f"{tax_pct}"}
        detail: Dict[str, Any] = {
            "currency_code": currency.upper(),
            "note": "Created by PayPilot (PayPal AI Hackathon).",
        }
        if invoice_number:
            detail["invoice_number"] = invoice_number
        if days_valid:
            detail["payment_term"] = {
                "term_type": "NET_" + str(days_valid),
                "due_date": (now + timedelta(days=days_valid)).strftime("%Y-%m-%d"),
            }
        payload = {
            "detail": detail,
            "invoicer": {"name": {"given_name": os.environ.get(
                "PAYPAL_MERCHANT_NAME", "PayPilot Merchant")}},
            "primary_recipients": [{
                "billing_info": {"email_address": recipient_email}}],
            "items": [item],
        }
        inv = self._request("POST", "/v2/invoicing/invoices",
                            payload, idempotency_key=str(uuid4()))
        return self._shape_invoice(inv)

    def send_invoice(self, invoice_id: str) -> Dict[str, Any]:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/send",
                      {"send_to_recipient": True,
                       "send_to_invoicer": False},
                      idempotency_key=str(uuid4()))
        return self.get_invoice(invoice_id)

    def list_invoices(self, status=None, page=1, page_size=10) -> Dict[str, Any]:
        params: Dict[str, str] = {"page": str(page), "page_size": str(page_size),
                                  "total_required": "true"}
        data = self._request("GET", "/v2/invoicing/invoices", params=params)
        invs = [self._shape_invoice(i) for i in data.get("items", [])]
        if status:
            invs = [i for i in invs if i["status"] == status.upper()]
        return {"invoices": invs,
                "total": data.get("total_items", len(invs)), "page": page}

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        return self._shape_invoice(
            self._request("GET", f"/v2/invoicing/invoices/{invoice_id}"))

    def remind_invoice(self, invoice_id: str) -> Dict[str, Any]:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/remind",
                      {"subject": "Friendly payment reminder",
                       "note": "Just a reminder that this invoice is due.",
                       "send_to_recipient": True},
                      idempotency_key=str(uuid4()))
        return self.get_invoice(invoice_id)

    def cancel_invoice(self, invoice_id: str) -> Dict[str, Any]:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/cancel",
                      {"subject": "Invoice cancelled",
                       "note": "Cancelled via PayPilot.",
                       "send_to_recipient": True,
                       "send_to_invoicer": False},
                      idempotency_key=str(uuid4()))
        return self.get_invoice(invoice_id)

    # ---------- orders ----------
    def create_order(self, *, amount, currency="USD",
                     description="Payment") -> Dict[str, Any]:
        if amount is None or amount <= 0:
            raise ValueError("Order amount must be positive.")
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "description": description,
                "amount": {"currency_code": currency.upper(),
                           "value": f"{amount:.2f}"},
            }],
        }
        order = self._request("POST", "/v2/checkout/orders", payload,
                              idempotency_key=str(uuid4()))
        return self._shape_order(order)

    def get_order(self, order_id: str) -> Dict[str, Any]:
        return self._shape_order(
            self._request("GET", f"/v2/checkout/orders/{order_id}"))
