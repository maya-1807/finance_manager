"""Tests for Phase 2, Task 5: Automatic Classification."""

import pytest

from ingestion.classifier import (
    ClassificationContext,
    _apply_billing_day_logic,
    _matches_keyword,
    classify_transaction,
)


# ---------------------------------------------------------------------------
# _matches_keyword
# ---------------------------------------------------------------------------

class TestMatchesKeyword:
    def test_contains_match(self):
        assert _matches_keyword("שופרסל דיל באר שבע", "שופרסל", "contains")

    def test_contains_no_match(self):
        assert not _matches_keyword("רמי לוי", "שופרסל", "contains")

    def test_exact_match(self):
        assert _matches_keyword("פז", "פז", "exact")

    def test_exact_no_match_when_extra_text(self):
        assert not _matches_keyword("פז YELLOW רוממה", "פז", "exact")

    def test_starts_with_match(self):
        assert _matches_keyword("פז YELLOW רוממה", "פז", "starts_with")

    def test_starts_with_no_match(self):
        assert not _matches_keyword("at פז station", "פז", "starts_with")

    def test_case_insensitive(self):
        assert _matches_keyword("SPOTIFY Premium", "spotify", "contains")
        assert _matches_keyword("spotify premium", "SPOTIFY", "exact") is False
        assert _matches_keyword("spotify premium", "spotify premium", "exact")

    def test_hebrew_comparison(self):
        # .lower() is no-op for Hebrew; comparison still works
        assert _matches_keyword("סופר פארם אשדוד", "סופר פארם", "contains")


# ---------------------------------------------------------------------------
# ClassificationContext
# ---------------------------------------------------------------------------

class TestClassificationContext:
    def test_loads_rules_sorted_by_priority(self, db):
        ctx = ClassificationContext(db)
        # Seed has starts_with for פז; all others are contains
        match_types = [r["match_type"] for r in ctx.classification_rules]
        # exact rules should come before starts_with, starts_with before contains
        seen_order = []
        for mt in match_types:
            if mt not in seen_order:
                seen_order.append(mt)
        assert seen_order.index("starts_with") < seen_order.index("contains")

    def test_loads_fixed_expenses(self, db):
        # Insert a fixed expense with keyword
        db.execute(
            "INSERT INTO accounts (name, bank, type) VALUES ('A', 'b', 'personal')"
        )
        db.execute(
            "INSERT INTO fixed_expenses (name, expected_amount, keyword) "
            "VALUES ('Rent', 5000, 'שכירות')"
        )
        db.commit()
        ctx = ClassificationContext(db)
        assert len(ctx.fixed_expenses) == 1
        assert ctx.fixed_expenses[0]["keyword"] == "שכירות"

    def test_loads_fixed_incomes(self, db):
        db.execute(
            "INSERT INTO accounts (name, bank, type) VALUES ('A', 'b', 'personal')"
        )
        db.execute(
            "INSERT INTO fixed_incomes (name, expected_amount, keyword) "
            "VALUES ('Salary', 15000, 'משכורת')"
        )
        db.commit()
        ctx = ClassificationContext(db)
        assert len(ctx.fixed_incomes) == 1
        assert ctx.fixed_incomes[0]["keyword"] == "משכורת"

    def test_loads_billing_days(self, db):
        db.execute(
            "INSERT INTO accounts (id, name, bank, type) VALUES (1, 'A', 'b', 'personal')"
        )
        db.execute(
            "INSERT INTO credit_cards (id, account_id, name, company, billing_day) "
            "VALUES (10, 1, 'Card', 'visa', 15)"
        )
        db.commit()
        ctx = ClassificationContext(db)
        assert ctx.billing_days == {10: 15}

    def test_billing_days_skips_null(self, db):
        db.execute(
            "INSERT INTO accounts (id, name, bank, type) VALUES (1, 'A', 'b', 'personal')"
        )
        db.execute(
            "INSERT INTO credit_cards (id, account_id, name, company) "
            "VALUES (10, 1, 'Card', 'visa')"
        )
        db.commit()
        ctx = ClassificationContext(db)
        assert 10 not in ctx.billing_days


# ---------------------------------------------------------------------------
# classify_transaction — category_id from classification_rules
# ---------------------------------------------------------------------------

class TestClassifyCategory:
    def test_known_merchant_gets_category(self, db):
        txn = _make_txn("שופרסל דיל איקאה")
        classify_transaction(db, txn)
        assert txn["category_id"] == 2  # Food

    def test_spotify_subscriptions(self, db):
        txn = _make_txn("SPOTIFYIL              STOCKHOLM     SE")
        classify_transaction(db, txn)
        assert txn["category_id"] == 8  # Subscriptions

    def test_super_pharm_health(self, db):
        txn = _make_txn("סופר פארם נוה שאנן")
        classify_transaction(db, txn)
        assert txn["category_id"] == 5  # Health

    def test_dor_alon_transport(self, db):
        txn = _make_txn("דור אלון ממר\"צ")
        classify_transaction(db, txn)
        assert txn["category_id"] == 3  # Transport

    def test_paz_starts_with_transport(self, db):
        txn = _make_txn("פז YELLOW רוממה")
        classify_transaction(db, txn)
        assert txn["category_id"] == 3  # Transport

    def test_no_match_falls_back_to_uncategorized(self, db):
        txn = _make_txn("totally unknown merchant xyz")
        classify_transaction(db, txn)
        assert txn["category_id"] == 1  # Uncategorized

    def test_exact_beats_contains(self, db):
        """If both exact and contains rules exist, exact wins."""
        # Add an exact rule that maps "פז" to Entertainment(4)
        db.execute(
            "INSERT INTO classification_rules (category_id, keyword, match_type) "
            "VALUES (4, 'פז', 'exact')"
        )
        db.commit()
        txn = _make_txn("פז")
        classify_transaction(db, txn)
        assert txn["category_id"] == 4  # exact rule won

    def test_starts_with_beats_contains(self, db):
        """starts_with rule matches before a contains rule for the same keyword."""
        # The seed has פז starts_with → Transport(3)
        # Add a contains rule for פז → Entertainment(4)
        db.execute(
            "INSERT INTO classification_rules (category_id, keyword, match_type) "
            "VALUES (4, 'פז', 'contains')"
        )
        db.commit()
        txn = _make_txn("פז YELLOW רוממה")
        classify_transaction(db, txn)
        assert txn["category_id"] == 3  # starts_with wins


# ---------------------------------------------------------------------------
# classify_transaction — transaction_type logic
# ---------------------------------------------------------------------------

class TestClassifyTransactionType:
    def test_rule_match_no_fixed_gives_variable_expense(self, db):
        txn = _make_txn("שופרסל דיל")
        classify_transaction(db, txn)
        assert txn["transaction_type"] == "variable_expense"

    def test_no_match_at_all_gives_none(self, db):
        txn = _make_txn("unknown merchant")
        classify_transaction(db, txn)
        assert txn["transaction_type"] is None

    def test_fixed_expense_keyword_sets_type(self, db):
        db.execute(
            "INSERT INTO fixed_expenses (name, expected_amount, keyword) "
            "VALUES ('Rent', 5000, 'שכירות')"
        )
        db.commit()
        txn = _make_txn("שכירות חודשית")
        classify_transaction(db, txn)
        assert txn["transaction_type"] == "fixed_expense"

    def test_fixed_income_keyword_sets_type(self, db):
        db.execute(
            "INSERT INTO fixed_incomes (name, expected_amount, keyword) "
            "VALUES ('Salary', 15000, 'משכורת')"
        )
        db.commit()
        txn = _make_txn("העברת משכורת")
        classify_transaction(db, txn)
        assert txn["transaction_type"] == "income"

    def test_fixed_expense_takes_priority_over_fixed_income(self, db):
        db.execute(
            "INSERT INTO fixed_expenses (name, expected_amount, keyword) "
            "VALUES ('X', 100, 'dupkeyword')"
        )
        db.execute(
            "INSERT INTO fixed_incomes (name, expected_amount, keyword) "
            "VALUES ('Y', 200, 'dupkeyword')"
        )
        db.commit()
        txn = _make_txn("dupkeyword transaction")
        classify_transaction(db, txn)
        assert txn["transaction_type"] == "fixed_expense"

    def test_rule_and_fixed_expense_both_match(self, db):
        """category_id comes from rule, transaction_type from fixed_expense."""
        db.execute(
            "INSERT INTO fixed_expenses (name, expected_amount, keyword) "
            "VALUES ('Groceries', 2000, 'שופרסל')"
        )
        db.commit()
        txn = _make_txn("שופרסל דיל")
        classify_transaction(db, txn)
        assert txn["category_id"] == 2  # From classification rule
        assert txn["transaction_type"] == "fixed_expense"  # From fixed_expense

    def test_fixed_expense_no_rule_match(self, db):
        """fixed_expense matches but no classification_rule → category_id=1."""
        db.execute(
            "INSERT INTO fixed_expenses (name, expected_amount, keyword) "
            "VALUES ('Rent', 5000, 'noruleforthisthing')"
        )
        db.commit()
        txn = _make_txn("noruleforthisthing payment")
        classify_transaction(db, txn)
        assert txn["category_id"] == 1
        assert txn["transaction_type"] == "fixed_expense"


# ---------------------------------------------------------------------------
# classify_transaction — edge cases
# ---------------------------------------------------------------------------

class TestClassifyEdgeCases:
    def test_empty_description(self, db):
        txn = _make_txn("")
        classify_transaction(db, txn)
        assert txn["category_id"] == 1
        assert txn["transaction_type"] is None

    def test_none_description(self, db):
        txn = _make_txn(None)
        classify_transaction(db, txn)
        assert txn["category_id"] == 1
        assert txn["transaction_type"] is None

    def test_whitespace_only_description(self, db):
        txn = _make_txn("   ")
        classify_transaction(db, txn)
        assert txn["category_id"] == 1
        assert txn["transaction_type"] is None

    def test_ctx_reuse(self, db):
        """ClassificationContext can be reused across multiple transactions."""
        ctx = ClassificationContext(db)
        txn1 = _make_txn("שופרסל דיל")
        txn2 = _make_txn("SPOTIFY Premium")
        classify_transaction(db, txn1, ctx=ctx)
        classify_transaction(db, txn2, ctx=ctx)
        assert txn1["category_id"] == 2
        assert txn2["category_id"] == 8

    def test_classify_creates_ctx_if_none(self, db):
        txn = _make_txn("שופרסל דיל")
        classify_transaction(db, txn, ctx=None)
        assert txn["category_id"] == 2

    def test_modifies_txn_in_place(self, db):
        txn = _make_txn("שופרסל")
        result = classify_transaction(db, txn)
        assert result is txn  # same object returned


# ---------------------------------------------------------------------------
# _apply_billing_day_logic
# ---------------------------------------------------------------------------

class TestBillingDayLogic:
    def test_day_before_billing_day_current_month(self):
        billing_days = {1: 15}
        txn = {"source_type": "credit_card", "source_id": 1, "date": "2025-06-10"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] == "2025-06"

    def test_day_on_billing_day_current_month(self):
        billing_days = {1: 15}
        txn = {"source_type": "credit_card", "source_id": 1, "date": "2025-06-15"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] == "2025-06"

    def test_day_after_billing_day_next_month(self):
        billing_days = {1: 15}
        txn = {"source_type": "credit_card", "source_id": 1, "date": "2025-06-16"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] == "2025-07"

    def test_december_rolls_to_january(self):
        billing_days = {1: 10}
        txn = {"source_type": "credit_card", "source_id": 1, "date": "2025-12-25"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] == "2026-01"

    def test_december_before_billing_day(self):
        billing_days = {1: 28}
        txn = {"source_type": "credit_card", "source_id": 1, "date": "2025-12-15"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] == "2025-12"

    def test_bank_account_skipped(self):
        billing_days = {1: 15}
        txn = {"source_type": "bank", "source_id": 1, "date": "2025-06-20"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] is None

    def test_no_billing_day_for_card(self):
        billing_days = {}  # card not in map
        txn = {"source_type": "credit_card", "source_id": 99, "date": "2025-06-20"}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] is None

    def test_no_date(self):
        billing_days = {1: 15}
        txn = {"source_type": "credit_card", "source_id": 1, "date": None}
        _apply_billing_day_logic(txn, billing_days)
        assert txn["charged_month"] is None

    def test_billing_day_2(self):
        """Matches the real config: billing_day=2."""
        billing_days = {3: 2}
        # Day 1 <= 2 → current month
        txn1 = {"source_type": "credit_card", "source_id": 3, "date": "2026-01-01"}
        _apply_billing_day_logic(txn1, billing_days)
        assert txn1["charged_month"] == "2026-01"
        # Day 2 <= 2 → current month
        txn2 = {"source_type": "credit_card", "source_id": 3, "date": "2026-01-02"}
        _apply_billing_day_logic(txn2, billing_days)
        assert txn2["charged_month"] == "2026-01"
        # Day 3 > 2 → next month
        txn3 = {"source_type": "credit_card", "source_id": 3, "date": "2026-01-03"}
        _apply_billing_day_logic(txn3, billing_days)
        assert txn3["charged_month"] == "2026-02"


# ---------------------------------------------------------------------------
# classify_transaction — billing day integration
# ---------------------------------------------------------------------------

class TestClassifyWithBillingDay:
    def test_credit_card_gets_charged_month(self, db):
        db.execute(
            "INSERT INTO accounts (id, name, bank, type) VALUES (1, 'A', 'b', 'personal')"
        )
        db.execute(
            "INSERT INTO credit_cards (id, account_id, name, company, billing_day) "
            "VALUES (5, 1, 'Card', 'visa', 10)"
        )
        db.commit()
        txn = _make_txn("שופרסל", source_type="credit_card", source_id=5, date="2025-03-15")
        classify_transaction(db, txn)
        assert txn["charged_month"] == "2025-04"  # 15 > 10 → next month

    def test_bank_account_no_charged_month(self, db):
        txn = _make_txn("שופרסל", source_type="bank", source_id=1, date="2025-03-15")
        classify_transaction(db, txn)
        assert txn["charged_month"] is None


# ---------------------------------------------------------------------------
# Migration: charged_month column exists
# ---------------------------------------------------------------------------

class TestMigration:
    def test_charged_month_column_exists(self, db):
        cols = [row[1] for row in db.execute("PRAGMA table_info(transactions)").fetchall()]
        assert "charged_month" in cols

    def test_schema_version_is_2(self, db):
        ver = db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        assert ver == 2


# ---------------------------------------------------------------------------
# duplicate_checker — pending_to_completed with classification fields
# ---------------------------------------------------------------------------

class TestPendingToCompletedClassification:
    def test_updates_classification_fields(self, db):
        _setup_source(db)
        # Insert a pending transaction
        db.execute(
            "INSERT INTO transactions (source_type, source_id, date, amount, "
            "description, status, original_id, category_id, transaction_type) "
            "VALUES ('bank', 1, '2025-01-15', -100, 'test', 'pending', 'abc', 1, NULL)"
        )
        db.commit()
        row_id = db.execute("SELECT id FROM transactions WHERE original_id = 'abc'").fetchone()[0]

        from ingestion.duplicate_checker import update_pending_to_completed
        update_pending_to_completed(
            db, row_id, "abc", "2025-01-16", -100,
            category_id=5, transaction_type="variable_expense", charged_month="2025-01",
        )
        db.commit()

        updated = db.execute("SELECT * FROM transactions WHERE id = ?", (row_id,)).fetchone()
        assert updated["status"] == "completed"
        assert updated["category_id"] == 5
        assert updated["transaction_type"] == "variable_expense"
        assert updated["charged_month"] == "2025-01"


# ---------------------------------------------------------------------------
# End-to-end: ingest_file with classification
# ---------------------------------------------------------------------------

class TestIngestWithClassification:
    def test_ingested_transactions_are_classified(self, db, tmp_path):
        _setup_source(db)
        json_file = _write_scraper_json(tmp_path, "leumi", "1234", [
            {"description": "שופרסל דיל", "date": "2025-06-10T00:00:00Z",
             "chargedAmount": -200, "status": "completed"},
            {"description": "SPOTIFY Premium", "date": "2025-06-12T00:00:00Z",
             "chargedAmount": -30, "status": "completed"},
            {"description": "unknown thing", "date": "2025-06-13T00:00:00Z",
             "chargedAmount": -50, "status": "completed"},
        ])

        from ingestion.ingest import ingest_file
        result = ingest_file(json_file, db=db)
        assert result["inserted"] == 3

        rows = db.execute(
            "SELECT description, category_id, transaction_type "
            "FROM transactions ORDER BY date"
        ).fetchall()

        # שופרסל → Food(2), variable_expense
        assert rows[0]["category_id"] == 2
        assert rows[0]["transaction_type"] == "variable_expense"
        # SPOTIFY → Subscriptions(8), variable_expense
        assert rows[1]["category_id"] == 8
        assert rows[1]["transaction_type"] == "variable_expense"
        # unknown → Uncategorized(1), None
        assert rows[2]["category_id"] == 1
        assert rows[2]["transaction_type"] is None

    def test_ingested_credit_card_gets_charged_month(self, db, tmp_path):
        _setup_credit_card_source(db, billing_day=10)
        json_file = _write_scraper_json(tmp_path, "visa", "9999", [
            {"description": "some purchase", "date": "2025-06-15T00:00:00Z",
             "chargedAmount": -100, "status": "completed"},
        ])

        from ingestion.ingest import ingest_file
        result = ingest_file(json_file, db=db)
        assert result["inserted"] == 1

        row = db.execute("SELECT charged_month FROM transactions").fetchone()
        assert row["charged_month"] == "2025-07"  # 15 > 10 → next month

    def test_ingested_bank_no_charged_month(self, db, tmp_path):
        _setup_source(db)
        json_file = _write_scraper_json(tmp_path, "leumi", "1234", [
            {"description": "some purchase", "date": "2025-06-15T00:00:00Z",
             "chargedAmount": -100, "status": "completed"},
        ])

        from ingestion.ingest import ingest_file
        result = ingest_file(json_file, db=db)
        assert result["inserted"] == 1

        row = db.execute("SELECT charged_month FROM transactions").fetchone()
        assert row["charged_month"] is None

    def test_pending_to_completed_gets_classification(self, db, tmp_path):
        _setup_source(db)
        # Pre-insert a pending transaction
        db.execute(
            "INSERT INTO transactions (source_type, source_id, date, amount, "
            "description, status, original_id, category_id, transaction_type, currency) "
            "VALUES ('bank', 1, '2025-06-10', -200, 'שופרסל דיל', 'pending', 'txn-1', 1, NULL, 'ILS')"
        )
        db.commit()

        # Ingest a completed version of the same transaction
        json_file = _write_scraper_json(tmp_path, "leumi", "1234", [
            {"description": "שופרסל דיל", "date": "2025-06-10T00:00:00Z",
             "chargedAmount": -200, "status": "completed", "identifier": "txn-1",
             "processedDate": "2025-06-11T00:00:00Z"},
        ])

        from ingestion.ingest import ingest_file
        result = ingest_file(json_file, db=db)
        assert result["updated"] == 1

        row = db.execute("SELECT * FROM transactions WHERE original_id = 'txn-1'").fetchone()
        assert row["status"] == "completed"
        assert row["category_id"] == 2  # Food — classified during update
        assert row["transaction_type"] == "variable_expense"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_txn(description, source_type="bank", source_id=1, date="2025-06-15"):
    return {
        "description": description,
        "source_type": source_type,
        "source_id": source_id,
        "date": date,
        "category_id": None,
        "transaction_type": None,
    }


def _setup_source(db):
    db.execute(
        "INSERT INTO accounts (id, name, bank, type, scraper_type) "
        "VALUES (1, 'Test Account', 'leumi', 'personal', 'leumi')"
    )
    db.commit()


def _setup_credit_card_source(db, billing_day=10):
    db.execute(
        "INSERT INTO accounts (id, name, bank, type) VALUES (1, 'A', 'b', 'personal')"
    )
    db.execute(
        "INSERT INTO credit_cards (id, account_id, name, company, last_4_digits, billing_day, scraper_type) "
        f"VALUES (1, 1, 'Card', 'visa', '9999', {billing_day}, 'visa')"
    )
    db.commit()


def _write_scraper_json(tmp_path, bank, account_number, txns):
    import json
    data = {
        "bank": bank,
        "scrapedAt": "2025-06-15T12:00:00Z",
        "accounts": [{"accountNumber": account_number, "txns": txns}],
    }
    f = tmp_path / f"{bank}_test.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f
