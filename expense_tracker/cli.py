"""Command-line interface. Run `python -m expense_tracker --help` for usage."""

from __future__ import annotations

import argparse
import sys

from .tracker import ExpenseTracker, ValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="expense_tracker", description="Track student expenses.")
    parser.add_argument("--db", default="expenses.db", help="path to the SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="record an expense")
    add.add_argument("amount")
    add.add_argument("-c", "--category", default="other")
    add.add_argument("-n", "--note", default="")
    add.add_argument("-d", "--date", dest="spent_on", help="YYYY-MM-DD (default: today)")

    lst = sub.add_parser("list", help="list expenses")
    lst.add_argument("-m", "--month", help="filter by YYYY-MM")

    summ = sub.add_parser("summary", help="total spending per category")
    summ.add_argument("-m", "--month", help="filter by YYYY-MM")

    bud = sub.add_parser("budget", help="set a monthly budget for a category")
    bud.add_argument("category")
    bud.add_argument("limit")

    dele = sub.add_parser("delete", help="delete an expense by id")
    dele.add_argument("expense_id", type=int)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with ExpenseTracker(args.db) as tracker:
            if args.command == "add":
                e = tracker.add_expense(args.amount, args.category, args.note, args.spent_on)
                print(f"Added #{e.id}: {e.amount} in '{e.category}' on {e.spent_on}")
            elif args.command == "list":
                for e in tracker.list_expenses(args.month):
                    print(f"#{e.id:<4} {e.spent_on}  {e.amount:>10}  {e.category:<14} {e.note}")
                print(f"Total: {tracker.total(args.month)}")
            elif args.command == "summary":
                totals = tracker.total_by_category(args.month)
                if not totals:
                    print("No expenses recorded.")
                for category, amount in totals.items():
                    print(f"{category:<14} {amount:>10}")
                print(f"{'TOTAL':<14} {tracker.total(args.month):>10}")
                for alert in tracker.budget_alerts(args.month):
                    print(f"WARNING: '{alert.category}' over budget by {alert.exceeded_by} "
                          f"(limit {alert.limit})")
            elif args.command == "budget":
                tracker.set_budget(args.category, args.limit)
                print(f"Budget for '{args.category}' set to {args.limit}")
            elif args.command == "delete":
                ok = tracker.delete_expense(args.expense_id)
                print("Deleted." if ok else f"No expense with id {args.expense_id}.")
                return 0 if ok else 1
    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0
