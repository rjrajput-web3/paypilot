"""Tests for the NL parser and the agent's end-to-end flows."""
import unittest

from paypilot.agent import Agent
from paypilot.mock_adapter import MockAdapter
from paypilot.nlp import rule_parse


class TestRuleParser(unittest.TestCase):
    def test_paypal_blog_example(self):
        # The exact example from PayPal's MCP announcement blog.
        intent = rule_parse(
            "Create a PayPal invoice link for painting a house with a cost of "
            "$450. Add 8% tax and apply 5% discount. "
            "Make sure it expires in 10 days.")
        self.assertEqual(intent.name, "create_invoice")
        self.assertEqual(intent.amount, 450.0)
        self.assertEqual(intent.tax_pct, 8.0)
        self.assertEqual(intent.discount_pct, 5.0)
        self.assertEqual(intent.days_valid, 10)
        self.assertIn("painting", intent.description or "")

    def test_intents(self):
        self.assertEqual(rule_parse("list my invoices").name, "list_invoices")
        self.assertEqual(rule_parse("send it").name, "send_invoice")
        self.assertEqual(
            rule_parse("remind the client about INV-PP-0001").name,
            "remind_invoice")
        self.assertEqual(
            rule_parse("cancel invoice INV-PP-0002").name, "cancel_invoice")
        self.assertEqual(
            rule_parse("what's the status of INV-PP-0001?").name,
            "invoice_status")
        self.assertEqual(
            rule_parse("create a $99 payment link for the Pro plan").name,
            "create_order")
        self.assertEqual(rule_parse("help").name, "help")
        self.assertEqual(rule_parse("blablabla nonsense").name, "unknown")

    def test_email_extraction(self):
        intent = rule_parse("create invoice for $100 web design to jane@acme.co")
        self.assertEqual(intent.name, "create_invoice")
        self.assertEqual(intent.email, "jane@acme.co")
        self.assertEqual(intent.amount, 100.0)


class TestAgentFlows(unittest.TestCase):
    def setUp(self):
        self.agent = Agent(MockAdapter())

    def test_full_invoice_conversation(self):
        r1 = self.agent.handle(
            "create an invoice for $450 for painting a house to "
            "client@example.com, 8% tax, 5% discount, expires in 10 days")
        self.assertIn("461.70", r1["reply"])          # totals computed
        self.assertIn("DEMO", r1["reply"])            # honest badge
        self.assertIn("send it", r1["reply"])         # agentic next-step

        r2 = self.agent.handle("send it")            # resolves last draft
        self.assertIn("Sent!", r2["reply"])
        self.assertEqual(r2["intent"]["name"], "send_invoice")

        r3 = self.agent.handle("what's the status of that invoice?")
        self.assertIn("SENT", r3["reply"])

    def test_slot_filling(self):
        r = self.agent.handle("create an invoice for $200")
        self.assertIn("email", r["reply"].lower())    # asks for missing slot

    def test_payment_link_flow(self):
        r = self.agent.handle("create a $99 payment link for the Pro plan")
        self.assertIn("checkoutnow", r["reply"])
        self.assertEqual(r["intent"]["name"], "create_order")

    def test_unknown_invoice_graceful(self):
        r = self.agent.handle("cancel invoice INV-PP-9999")
        self.assertIn("couldn't", r["reply"].lower())


if __name__ == "__main__":
    unittest.main()
