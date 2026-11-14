# Smart Expense Tracker

A lightweight command-line tool that helps students record daily expenses, see spending
per category, and receive warnings when a monthly category budget is exceeded.
Uses only the Python standard library (Python 3.10+) and SQLite.

## Usage

```bash
python -m expense_tracker add 250 -c food -n "Canteen lunch" -d 2026-01-05
python -m expense_tracker add 1200 -c rent -d 2026-01-01
python -m expense_tracker budget food 2000
python -m expense_tracker summary -m 2026-01
python -m expense_tracker list -m 2026-01
python -m expense_tracker delete 3
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```
expense_tracker/
  tracker.py   # validation, SQLite persistence, summaries, budget alerts
  cli.py       # argparse command-line interface
  __main__.py  # entry point: python -m expense_tracker
tests/
  test_tracker.py
```
