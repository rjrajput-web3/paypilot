"""Natural-language -> structured intent for PayPilot.

Two "brains", tried in order:
1. LLM brain — if LLM_API_KEY is set, an OpenAI-compatible chat-completions
   endpoint turns the utterance into JSON matching the Intent schema.
2. Rule brain — deterministic regex parser (always available, zero cost).

parse() always returns an Intent; .brain tells you which path was used.
The LLM path is optional, fully disclosed, and never required for the demo.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

INTENT_NAMES = [
    "create_invoice", "send_invoice", "list_invoices", "invoice_status",
    "remind_invoice", "cancel_invoice", "create_order", "order_status",
    "help", "unknown",
]


@dataclass
class Intent:
    name: str = "unknown"
    amount: Optional[float] = None
    currency: str = "USD"
    description: Optional[str] = None
    email: Optional[str] = None
    tax_pct: Optional[float] = None
    discount_pct: Optional[float] = None
    days_valid: Optional[int] = None
    invoice_id: Optional[str] = None
    order_id: Optional[str] = None
    brain: str = "rules"
    raw: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


# ---------------------------------------------------------------- rule brain
_MONEY = re.compile(r"(?:USD|EUR|INR|GBP|\$|€|₹|£)?\s?(\d+(?:\.\d{1,2})?)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_TAX = re.compile(r"(\d+(?:\.\d+)?)\s?%\s*(?:tax|gst|vat)")
_DISCOUNT = re.compile(r"(\d+(?:\.\d+)?)\s?%\s*(?:discount|off)")
_EXPIRE = re.compile(r"expir\w*\s+in\s+(\d+)\s*days?")
_INV_ID = re.compile(r"\bINV-[A-Za-z0-9-]+\b", re.IGNORECASE)
_ORD_ID = re.compile(r"\b\d[A-Za-z0-9]{6,}MOCK\b|\border\s+([A-Za-z0-9]{8,})\b", re.IGNORECASE)
_CCY = {"usd": "USD", "dollar": "USD", "eur": "EUR", "euro": "EUR",
        "inr": "INR", "rupee": "INR", "gbp": "GBP", "pound": "GBP"}


def _extract_amount(text: str) -> tuple[Optional[float], str]:
    currency = "USD"
    for word, code in _CCY.items():
        if word in text.lower():
            currency = code
            break
    # prefer a number near a money cue
    for m in _MONEY.finditer(text):
        window = text[max(0, m.start() - 12):m.end() + 12].lower()
        if any(c in window for c in ("$", "usd", "eur", "inr", "gbp", "cost",
                                     "for $", "amount", "price", "charge",
                                     "€", "₹", "£")):
            return float(m.group(1)), currency
    return None, currency


def _clean_description(text: str, email: Optional[str]) -> Optional[str]:
    t = text
    t = _EMAIL.sub(" ", t)
    t = _EXPIRE.sub(" ", t)   # before _MONEY strips the digits it needs
    t = _TAX.sub(" ", t)
    t = _DISCOUNT.sub(" ", t)
    t = _MONEY.sub(" ", t)
    for word in ("create", "new", "invoice", "invoices", "link", "links",
                 "for", "a", "an", "the", "with", "add", "apply", "and",
                 "make", "sure", "it", "paypal", "cost", "of", "to",
                 "payment", "generate", "please", "me", "my"):
        t = re.sub(r"\b" + word + r"\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"%\s*", " ", t)          # stray percent signs
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    t = re.sub(r"\s+(in\s+)?days?$", "", t, flags=re.IGNORECASE)  # residue
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    return t or None


def rule_parse(text: str) -> Intent:
    t = text.strip()
    low = t.lower()
    email_m = _EMAIL.search(t)
    email = email_m.group(0) if email_m else None
    inv_m = _INV_ID.search(t)
    ord_m = _ORD_ID.search(t)

    def base(**kw: Any) -> Intent:
        kw.setdefault("raw", t)
        kw.setdefault("brain", "rules")
        return Intent(**kw)

    if any(w in low for w in ("help", "what can you", "how do i", "commands")):
        return base(name="help")

    # bare confirmations rely on session memory ("send it" -> last draft)
    if low.strip() in ("send it", "yes send", "send it now", "go ahead and send",
                       "send the invoice"):
        return base(name="send_invoice")
    if low.strip() in ("cancel it", "yes cancel"):
        return base(name="cancel_invoice")

    mentions_invoice = "invoice" in low or inv_m is not None
    mentions_order = "order" in low or "payment link" in low or "checkout" in low or ord_m is not None

    # order intents first when explicitly about orders/links
    if mentions_order and not mentions_invoice:
        amount, currency = _extract_amount(t)
        if any(w in low for w in ("status", "track", "check", "where")) or ord_m:
            oid = None
            if ord_m:
                oid = ord_m.group(0) if not ord_m.groups() or not ord_m.group(1) else ord_m.group(1)
            return base(name="order_status", order_id=oid, amount=amount, currency=currency)
        if any(w in low for w in ("create", "new", "make", "generate", "link")):
            desc = _clean_description(t, email)
            return base(name="create_order", amount=amount, currency=currency,
                        description=desc)

    if mentions_invoice:
        amount, currency = _extract_amount(t)
        tax_m, disc_m, exp_m = _TAX.search(t), _DISCOUNT.search(t), _EXPIRE.search(t)
        iid = inv_m.group(0).upper() if inv_m else None
        if any(w in low for w in ("cancel", "void")):
            return base(name="cancel_invoice", invoice_id=iid)
        if any(w in low for w in ("remind", "nudge", "follow up", "follow-up")):
            return base(name="remind_invoice", invoice_id=iid)
        if any(w in low for w in ("status", "check", "track", "show", "get")) and \
                not any(w in low for w in ("create", "new", "make", "generate")):
            return base(name="invoice_status", invoice_id=iid)
        if any(w in low for w in ("list", "all", "show")) and \
                not any(w in low for w in ("create", "new", "make", "generate", "send")):
            return base(name="list_invoices")
        if any(w in low for w in ("send", "email it", "dispatch")):
            return base(name="send_invoice", invoice_id=iid)
        # default: create
        desc = _clean_description(t, email)
        return base(name="create_invoice", amount=amount, currency=currency,
                    description=desc, email=email,
                    tax_pct=float(tax_m.group(1)) if tax_m else None,
                    discount_pct=float(disc_m.group(1)) if disc_m else None,
                    days_valid=int(exp_m.group(1)) if exp_m else None,
                    invoice_id=iid)

    # generic list/show without the word invoice
    if any(w in low for w in ("list invoices", "show invoices", "my invoices")):
        return base(name="list_invoices")

    return base(name="unknown")


# ---------------------------------------------------------------- LLM brain
_LLM_SYSTEM = """You are PayPilot's intent parser. Convert the user's message into ONE JSON object with these fields:
{"name": one of create_invoice|send_invoice|list_invoices|invoice_status|remind_invoice|cancel_invoice|create_order|order_status|help|unknown,
 "amount": number or null, "currency": 3-letter code or "USD",
 "description": short service description or null, "email": email or null,
 "tax_pct": number or null, "discount_pct": number or null,
 "days_valid": number or null, "invoice_id": id or null, "order_id": id or null}
Return ONLY the JSON object."""


def llm_parse(text: str) -> Optional[Intent]:
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        return None
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    try:
        req = urllib.request.Request(
            base_url + "/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"]["content"]
        obj = json.loads(content)
        if obj.get("name") not in INTENT_NAMES:
            return None
        intent = Intent(raw=text, brain=f"llm:{model}")
        for k in ("name", "amount", "currency", "description", "email",
                  "tax_pct", "discount_pct", "days_valid", "invoice_id",
                  "order_id"):
            if k in obj and obj[k] is not None:
                setattr(intent, k, obj[k])
        return intent
    except Exception:
        return None


def parse(text: str) -> Intent:
    """LLM brain first (if configured), rule brain as guaranteed fallback."""
    intent = llm_parse(text)
    if intent is not None:
        return intent
    return rule_parse(text)
