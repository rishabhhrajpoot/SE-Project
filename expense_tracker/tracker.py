"""Core business logic: validation, persistence (SQLite), summaries and budget alerts."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_CATEGORIES = ("food", "transport", "books", "rent", "entertainment", "other")


class ValidationError(ValueError):
    """Raised when user input is invalid."""


@dataclass(frozen=True)
class Expense:
    id: int
    amount: Decimal
    category: str
    note: str
    spent_on: date


@dataclass(frozen=True)
class BudgetAlert:
    category: str
    limit: Decimal
    spent: Decimal

    @property
    def exceeded_by(self) -> Decimal:
        return self.spent - self.limit


def parse_amount(raw: str) -> Decimal:
    """Parse a money amount such as '250', '99.5' or '1,200.00' into a positive Decimal."""
    try:
        value = Decimal(raw.replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValidationError(f"invalid amount: {raw!r}") from exc
    if not value.is_finite() or value <= 0:
        raise ValidationError("amount must be a positive number")
    if value.as_tuple().exponent < -2:
        raise ValidationError("amount may have at most two decimal places")
    return value.quantize(Decimal("0.01"))


def parse_date(raw: str | None) -> date:
    """Parse an ISO date (YYYY-MM-DD); None means today."""
    if raw is None:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"invalid date {raw!r}, expected YYYY-MM-DD") from exc


class ExpenseTracker:
    """Stores expenses in SQLite. Pass ':memory:' for an in-memory database (tests)."""

    def __init__(self, db_path: str | Path = "expenses.db") -> None:
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                   category TEXT NOT NULL,
                   note TEXT NOT NULL DEFAULT '',
                   spent_on TEXT NOT NULL
               )"""
        )
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS budgets (
                   category TEXT PRIMARY KEY,
                   limit_cents INTEGER NOT NULL CHECK (limit_cents > 0)
               )"""
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ExpenseTracker":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # ----- write operations -------------------------------------------------
    def add_expense(
        self,
        amount: str | Decimal,
        category: str = "other",
        note: str = "",
        spent_on: str | None = None,
    ) -> Expense:
        value = amount if isinstance(amount, Decimal) else parse_amount(amount)
        if value <= 0:
            raise ValidationError("amount must be positive")
        category = category.strip().lower() or "other"
        day = parse_date(spent_on)
        cents = int(value * 100)
        cur = self._conn.execute(
            "INSERT INTO expenses (amount_cents, category, note, spent_on) VALUES (?, ?, ?, ?)",
            (cents, category, note.strip(), day.isoformat()),
        )
        self._conn.commit()
        return Expense(cur.lastrowid, Decimal(cents) / 100, category, note.strip(), day)

    def delete_expense(self, expense_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def set_budget(self, category: str, limit: str | Decimal) -> None:
        value = limit if isinstance(limit, Decimal) else parse_amount(limit)
        self._conn.execute(
            "INSERT INTO budgets (category, limit_cents) VALUES (?, ?) "
            "ON CONFLICT(category) DO UPDATE SET limit_cents = excluded.limit_cents",
            (category.strip().lower(), int(value * 100)),
        )
        self._conn.commit()

    # ----- read operations --------------------------------------------------
    def list_expenses(self, month: str | None = None) -> list[Expense]:
        """List expenses, newest first. `month` is an optional 'YYYY-MM' filter."""
        sql = "SELECT * FROM expenses"
        params: tuple = ()
        if month is not None:
            if len(month) != 7 or month[4] != "-":
                raise ValidationError("month must be in YYYY-MM format")
            sql += " WHERE substr(spent_on, 1, 7) = ?"
            params = (month,)
        sql += " ORDER BY spent_on DESC, id DESC"
        return [self._row_to_expense(r) for r in self._conn.execute(sql, params)]

    def total_by_category(self, month: str | None = None) -> dict[str, Decimal]:
        expenses = self.list_expenses(month)
        totals: dict[str, Decimal] = {}
        for e in expenses:
            totals[e.category] = totals.get(e.category, Decimal("0")) + e.amount
        return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))

    def total(self, month: str | None = None) -> Decimal:
        return sum((e.amount for e in self.list_expenses(month)), Decimal("0"))

    def budget_alerts(self, month: str | None = None) -> list[BudgetAlert]:
        """Return every category whose spending in the period exceeds its budget."""
        totals = self.total_by_category(month)
        alerts = []
        for row in self._conn.execute("SELECT category, limit_cents FROM budgets ORDER BY category"):
            limit = Decimal(row["limit_cents"]) / 100
            spent = totals.get(row["category"], Decimal("0"))
            if spent > limit:
                alerts.append(BudgetAlert(row["category"], limit, spent))
        return alerts

    @staticmethod
    def _row_to_expense(row: sqlite3.Row) -> Expense:
        return Expense(
            id=row["id"],
            amount=Decimal(row["amount_cents"]) / 100,
            category=row["category"],
            note=row["note"],
            spent_on=date.fromisoformat(row["spent_on"]),
        )
