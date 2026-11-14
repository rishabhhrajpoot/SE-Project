"""Smart Expense Tracker: a small, dependency-free personal finance tool."""

from .tracker import ExpenseTracker, Expense, BudgetAlert

__all__ = ["ExpenseTracker", "Expense", "BudgetAlert"]
__version__ = "1.0.0"
