import sqlite3


def check_duplicate(db: sqlite3.Connection, txn: dict) -> tuple[str, dict | None]:
    """Check if a transaction already exists in the database.

    Returns (action, existing_row) where action is one of:
    - "new": no match found
    - "duplicate": exact match found, skip
    - "pending_to_completed": existing pending record should be updated
    """
    original_id = txn.get("original_id")
    source_type = txn["source_type"]
    source_id = txn["source_id"]

    if original_id is not None:
        row = db.execute(
            "SELECT * FROM transactions WHERE original_id = ? AND source_type = ? AND source_id = ?",
            (original_id, source_type, source_id),
        ).fetchone()
        if row:
            existing = dict(row)
            if existing["status"] == "pending" and txn.get("status") == "completed":
                return "pending_to_completed", existing
            return "duplicate", existing

    # Fallback for pending txns without original_id
    if original_id is None and txn.get("status") == "pending":
        row = db.execute(
            "SELECT * FROM transactions WHERE date = ? AND amount = ? AND description = ? "
            "AND source_type = ? AND source_id = ?",
            (txn["date"], txn["amount"], txn.get("description"), source_type, source_id),
        ).fetchone()
        if row:
            return "duplicate", dict(row)

    return "new", None


def update_pending_to_completed(
    db: sqlite3.Connection,
    existing_id: int,
    original_id: str | None,
    processed_date: str | None,
    amount: float,
    category_id: int | None = None,
    transaction_type: str | None = None,
    charged_month: str | None = None,
) -> None:
    """Update a pending transaction to completed status."""
    db.execute(
        "UPDATE transactions SET status = 'completed', original_id = ?, "
        "processed_date = ?, amount = ?, category_id = ?, "
        "transaction_type = ?, charged_month = ? WHERE id = ?",
        (original_id, processed_date, amount, category_id,
         transaction_type, charged_month, existing_id),
    )
