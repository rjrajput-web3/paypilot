"""Tests for the MockAdapter: every invoice/order code path the agent uses."""
import unittest

from paypilot.mock_adapter import MockAdapter


class TestMockAdapter(unittest.TestCase):
    def setUp(self):
        self.a = MockAdapter()

    def test_invoice_lifecycle(self):
        inv = self.a.create_invoice(
            description="painting a house", amount=450.0, currency="USD",
            recipient_email="client@example.com", tax_pct=8.0,
            discount_pct=5.0, days_valid=10)
        self.assertEqual(inv["status"], "DRAFT")
        self.assertEqual(inv["id"], "INV-PP-0001")
        # 450 - 5% = 427.50 ; +8% tax = 461.70
        self.assertAlmostEqual(inv["total"], 461.70)
        self.assertIn("share", inv["links"])

        sent = self.a.send_invoice(inv["id"])
        self.assertEqual(sent["status"], "SENT")

        fetched = self.a.get_invoice(inv["id"])
        self.assertEqual(fetched["status"], "SENT")

        reminded = self.a.remind_invoice(inv["id"])
        self.assertEqual(reminded["reminders_sent"], 1)

    def test_cancel_invoice(self):
        inv = self.a.create_invoice(description="x", amount=10.0,
                                    recipient_email="a@b.co")
        cancelled = self.a.cancel_invoice(inv["id"])
        self.assertEqual(cancelled["status"], "CANCELLED")

    def test_list_invoices(self):
        self.a.create_invoice(description="one", amount=10.0,
                              recipient_email="a@b.co")
        self.a.create_invoice(description="two", amount=20.0,
                              recipient_email="a@b.co")
        data = self.a.list_invoices()
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["invoices"]), 2)

    def test_order_lifecycle(self):
        order = self.a.create_order(amount=99.0, currency="USD",
                                    description="Pro plan")
        self.assertEqual(order["status"], "CREATED")
        self.assertTrue(order["approve_url"].startswith("https://"))
        fetched = self.a.get_order(order["id"])
        self.assertEqual(fetched["id"], order["id"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.a.create_invoice(description="x", amount=0,
                                  recipient_email="a@b.co")
        with self.assertRaises(KeyError):
            self.a.get_invoice("INV-PP-9999")


if __name__ == "__main__":
    unittest.main()
