"""PayPilot CLI.

Usage:
    python3 -m paypilot.cli demo     # scripted end-to-end demo transcript
    python3 -m paypilot.cli chat     # interactive REPL

Honours PAYPAL_MODE like the web app: mock by default, real sandbox with
PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET set (see .env.example).
"""
from __future__ import annotations

import sys

from .adapter import pick_adapter
from .agent import Agent

DEMO_TURNS = [
    "Create a PayPal invoice link for painting a house with a cost of $450 "
    "to client@example.com. Add 8% tax and apply 5% discount. "
    "Make sure it expires in 10 days.",
    "send it",
    "what's the status of that invoice?",
    "Create a $99 payment link for the Pro plan subscription",
    "list my invoices",
    "remind the client about the first invoice",
]


def run_demo() -> None:
    adapter = pick_adapter()
    agent = Agent(adapter)
    print("=" * 72)
    print(f"PayPilot demo  ·  backend: {adapter.name}")
    print("=" * 72)
    for i, turn in enumerate(DEMO_TURNS, 1):
        print(f"\n[{i}] YOU: {turn}")
        result = agent.handle(turn)
        print(f"    PAYPILOT ({result['intent']['name']}):")
        for line in result["reply"].splitlines():
            print(f"    {line}")
    print("\n" + "=" * 72)
    print("Demo complete. Every step above ran through the real agent pipeline")
    print("(NL parse -> plan -> adapter calls -> reply) — no hardcoding.")


def run_chat() -> None:
    adapter = pick_adapter()
    agent = Agent(adapter)
    print(f"PayPilot chat · backend: {adapter.name} · type 'quit' to exit")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit"):
            break
        if not text:
            continue
        print("paypilot>", agent.handle(text)["reply"])


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if mode == "chat":
        run_chat()
    else:
        run_demo()


if __name__ == "__main__":
    main()
