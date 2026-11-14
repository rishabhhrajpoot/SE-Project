import unittest
from datetime import date
from decimal import Decimal

from expense_tracker import ExpenseTracker
from expense_tracker.tracker import ValidationError, parse_amount, parse_date


class ParsingTests(unittest.TestCase):
    def test_parse_amount_accepts_common_forms(self):
        self.assertEqual(parse_amount("250"), Decimal("250.00"))
        self.assertEqual(parse_amount("99.5"), Decimal("99.50"))
        self.assertEqual(parse_amount("1,200.25"), Decimal("1200.25"))

    def test_parse_amount_rejects_bad_input(self):
        for bad in ["abc", "0", "-5", "10.555", "nan", ""]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                parse_amount(bad)

    def test_parse_date(self):
        self.assertEqual(parse_date("2026-03-14"), date(2026, 3, 14))
        with self.assertRaises(ValidationError):
            parse_date("14/03/2026")


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.t = ExpenseTracker(":memory:")

    def tearDown(self):
        self.t.close()

    def test_add_and_list(self):
        e = self.t.add_expense("120", "Food", "lunch", "2026-01-05")
        self.assertEqual(e.category, "food")  # normalised to lower case
        rows = self.t.list_expenses()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].amount, Decimal("120.00"))

    def test_month_filter_and_total(self):
        self.t.add_expense("100", "food", spent_on="2026-01-10")
        self.t.add_expense("50", "books", spent_on="2026-02-10")
        self.assertEqual(self.t.total("2026-01"), Decimal("100.00"))
        self.assertEqual(self.t.total(), Decimal("150.00"))
        with self.assertRaises(ValidationError):
            self.t.list_expenses("2026/01")

    def test_summary_sorted_by_amount(self):
        self.t.add_expense("10", "books", spent_on="2026-01-01")
        self.t.add_expense("90", "rent", spent_on="2026-01-01")
        self.assertEqual(list(self.t.total_by_category("2026-01")), ["rent", "books"])

    def test_budget_alert_triggers_only_when_exceeded(self):
        self.t.set_budget("food", "200")
        self.t.add_expense("150", "food", spent_on="2026-01-02")
        self.assertEqual(self.t.budget_alerts("2026-01"), [])
        self.t.add_expense("75", "food", spent_on="2026-01-03")
        alerts = self.t.budget_alerts("2026-01")
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].exceeded_by, Decimal("25.00"))

    def test_set_budget_updates_existing(self):
        self.t.set_budget("food", "100")
        self.t.set_budget("food", "500")
        self.t.add_expense("300", "food", spent_on="2026-01-02")
        self.assertEqual(self.t.budget_alerts("2026-01"), [])

    def test_delete(self):
        e = self.t.add_expense("20", "food")
        self.assertTrue(self.t.delete_expense(e.id))
        self.assertFalse(self.t.delete_expense(e.id))


if __name__ == "__main__":
    unittest.main()
