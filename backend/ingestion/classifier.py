"""Automatic transaction classification.

Matches transaction descriptions against classification_rules,
fixed_expenses, and fixed_incomes keywords. Also applies billing day
logic for credit card transactions.
"""

import sqlite3
from datetime import date


class ClassificationContext:
    """Cache of classification data, loaded once per ingestion batch."""

    def __init__(self, db: sqlite3.Connection):
        # Sort rules so exact > starts_with > contains for priority ordering
        _type_order = {"exact": 0, "starts_with": 1, "contains": 2}
        rules = db.execute(
            "SELECT category_id, keyword, match_type FROM classification_rules"
        ).fetchall()
        self.classification_rules = sorted(
            [dict(r) for r in rules],
            key=lambda r: _type_order.get(r["match_type"], 99),
        )

        self.fixed_expenses = [
            dict(r) for r in db.execute(
                "SELECT id, keyword FROM fixed_expenses WHERE keyword IS NOT NULL"
            ).fetchall()
        ]

        self.fixed_incomes = [
            dict(r) for r in db.execute(
                "SELECT id, keyword FROM fixed_incomes WHERE keyword IS NOT NULL"
            ).fetchall()
        ]

        self.billing_days = {}
        for r in db.execute("SELECT id, billing_day FROM credit_cards").fetchall():
            if r["billing_day"] is not None:
                self.billing_days[r["id"]] = r["billing_day"]


def _matches_keyword(description: str, keyword: str, match_type: str) -> bool:
    """Case-insensitive keyword matching."""
    desc = description.lower()
    kw = keyword.lower()
    if match_type == "exact":
        return desc == kw
    elif match_type == "starts_with":
        return desc.startswith(kw)
    else:  # contains
        return kw in desc


def classify_transaction(db: sqlite3.Connection, txn: dict, ctx: ClassificationContext | None = None) -> dict:
    """Classify a transaction in-place. Returns the modified txn dict.

    Priority:
    1. classification_rules → category_id (exact > starts_with > contains)
    2. fixed_expenses keywords → transaction_type = "fixed_expense"
    3. fixed_incomes keywords → transaction_type = "income"
    4. Rules matched but no fixed match → transaction_type = "variable_expense"
    5. No match → category_id = 1, transaction_type = None
    """
    if ctx is None:
        ctx = ClassificationContext(db)

    description = txn.get("description") or ""
    if not description.strip():
        txn["category_id"] = 1
        txn["transaction_type"] = None
        _apply_billing_day_logic(txn, ctx.billing_days)
        return txn

    # Step 1: Match classification rules (already sorted by priority)
    rule_matched = False
    for rule in ctx.classification_rules:
        if _matches_keyword(description, rule["keyword"], rule["match_type"]):
            txn["category_id"] = rule["category_id"]
            rule_matched = True
            break

    if not rule_matched:
        txn["category_id"] = 1

    # Step 2: Match fixed_expenses
    fixed_matched = False
    for fe in ctx.fixed_expenses:
        if fe["keyword"] and fe["keyword"].lower() in description.lower():
            txn["transaction_type"] = "fixed_expense"
            fixed_matched = True
            break

    # Step 3: Match fixed_incomes (only if no fixed_expense matched)
    if not fixed_matched:
        for fi in ctx.fixed_incomes:
            if fi["keyword"] and fi["keyword"].lower() in description.lower():
                txn["transaction_type"] = "income"
                fixed_matched = True
                break

    # Step 4/5: Determine transaction_type when no fixed match
    if not fixed_matched:
        if rule_matched:
            txn["transaction_type"] = "variable_expense"
        else:
            txn["transaction_type"] = None

    _apply_billing_day_logic(txn, ctx.billing_days)
    return txn


def _apply_billing_day_logic(txn: dict, billing_days: dict) -> None:
    """Set charged_month for credit card transactions based on billing day.

    day <= billing_day → charged_month = current month
    day > billing_day → charged_month = next month
    """
    txn.setdefault("charged_month", None)

    if txn.get("source_type") != "credit_card":
        return

    billing_day = billing_days.get(txn.get("source_id"))
    if billing_day is None:
        return

    txn_date_str = txn.get("date")
    if not txn_date_str:
        return

    txn_date = date.fromisoformat(txn_date_str)
    if txn_date.day <= billing_day:
        charged = txn_date.replace(day=1)
    else:
        # Next month
        if txn_date.month == 12:
            charged = date(txn_date.year + 1, 1, 1)
        else:
            charged = date(txn_date.year, txn_date.month + 1, 1)

    txn["charged_month"] = charged.strftime("%Y-%m")
