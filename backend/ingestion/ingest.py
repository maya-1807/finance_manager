"""Transaction ingestion pipeline.

Reads scraper JSON output, normalizes transactions, deduplicates,
inserts into the database, stores balance snapshots, and logs results.

Usage:
    cd backend && python -m ingestion.ingest                    # ingest latest files
    cd backend && python -m ingestion.ingest path/to/file.json  # ingest specific file
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from db.database import get_connection
from ingestion.duplicate_checker import check_duplicate, update_pending_to_completed

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data-fetcher" / "output"


def _normalize_date(iso_str: str | None) -> str | None:
    """Parse UTC ISO 8601 string and convert to Israel date (YYYY-MM-DD)."""
    if not iso_str:
        return None
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    israel_dt = dt.astimezone(ISRAEL_TZ)
    return israel_dt.strftime("%Y-%m-%d")


def _normalize_transaction(txn: dict, source_type: str, source_id: int, bank: str) -> dict:
    """Convert a scraper transaction dict to a DB-ready dict."""
    charged = txn.get("chargedAmount", 0)
    original = txn.get("originalAmount", 0)

    # For pending Max txns where chargedAmount is 0, use originalAmount
    if bank == "max" and txn.get("status") == "pending" and charged == 0:
        amount = original
    else:
        amount = charged

    # Currency: prefer chargedCurrency, fallback originalCurrency, default ILS
    currency = txn.get("chargedCurrency") or txn.get("originalCurrency") or "ILS"

    identifier = txn.get("identifier")
    original_id = str(identifier) if identifier is not None else None

    memo = txn.get("memo")
    notes = memo if memo else None

    return {
        "source_type": source_type,
        "source_id": source_id,
        "date": _normalize_date(txn.get("date")),
        "processed_date": _normalize_date(txn.get("processedDate")),
        "amount": amount,
        "currency": currency,
        "description": txn.get("description"),
        "category_id": None,
        "transaction_type": None,
        "status": txn.get("status", "completed"),
        "installment_number": txn.get("installmentNumber"),
        "installment_total": txn.get("installmentTotal"),
        "original_id": original_id,
        "notes": notes,
    }


def _resolve_source(db: sqlite3.Connection, bank: str, account_number: str) -> tuple[str, int] | None:
    """Resolve a scraper account to (source_type, source_id).

    Bank accounts match on scraper_type = bank name.
    Credit cards match on scraper_type or last_4_digits = accountNumber.
    """
    # Try credit cards — prefer exact last_4_digits match, fallback to scraper_type
    row = db.execute(
        "SELECT id FROM credit_cards WHERE last_4_digits = ?",
        (account_number,),
    ).fetchone()
    if row:
        return "credit_card", row["id"]

    row = db.execute(
        "SELECT id FROM credit_cards WHERE scraper_type = ?",
        (bank,),
    ).fetchone()
    if row:
        return "credit_card", row["id"]

    # Try bank accounts
    row = db.execute(
        "SELECT id FROM accounts WHERE scraper_type = ?",
        (bank,),
    ).fetchone()
    if row:
        return "bank", row["id"]

    return None


def _insert_transaction(db: sqlite3.Connection, txn: dict) -> int:
    """Insert a transaction and return the new row id."""
    cols = [
        "source_type", "source_id", "date", "processed_date", "amount",
        "currency", "description", "category_id", "transaction_type",
        "status", "installment_number", "installment_total", "original_id", "notes",
    ]
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    values = [txn[c] for c in cols]
    cursor = db.execute(
        f"INSERT INTO transactions ({col_names}) VALUES ({placeholders})",
        values,
    )
    return cursor.lastrowid


def _upsert_balance_snapshot(db: sqlite3.Connection, account_id: int, date: str, balance: float) -> None:
    """Insert or update a balance snapshot for a bank account."""
    existing = db.execute(
        "SELECT id FROM balance_snapshots WHERE account_id = ? AND date = ?",
        (account_id, date),
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE balance_snapshots SET balance = ? WHERE id = ?",
            (balance, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO balance_snapshots (account_id, date, balance) VALUES (?, ?, ?)",
            (account_id, date, balance),
        )


def _log_scrape(db: sqlite3.Connection, source_type: str, source_id: int,
                status: str, count: int, error: str | None = None) -> None:
    """Insert a scrape log entry."""
    db.execute(
        "INSERT INTO scrape_log (source_type, source_id, status, transactions_count, error_message) "
        "VALUES (?, ?, ?, ?, ?)",
        (source_type, source_id, status, count, error),
    )


def ingest_file(file_path: str | Path, db: sqlite3.Connection | None = None) -> dict:
    """Process one scraper JSON file.

    Returns {"file", "inserted", "updated", "skipped", "errors"}.
    """
    file_path = Path(file_path)
    close_db = db is None
    if db is None:
        db = get_connection()

    result = {"file": str(file_path), "inserted": 0, "updated": 0, "skipped": 0, "errors": []}

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        bank = data["bank"]
        scrape_date = _normalize_date(data.get("scrapedAt")) or datetime.now(ISRAEL_TZ).strftime("%Y-%m-%d")

        for account in data.get("accounts", []):
            account_number = account.get("accountNumber", "")
            source = _resolve_source(db, bank, account_number)

            if source is None:
                error_msg = f"No matching account/card for bank={bank}, accountNumber={account_number}"
                result["errors"].append(error_msg)
                print(f"  ERROR: {error_msg}")
                continue

            source_type, source_id = source
            txns = account.get("txns", [])
            account_inserted = 0
            account_updated = 0
            account_skipped = 0

            for raw_txn in txns:
                try:
                    txn = _normalize_transaction(raw_txn, source_type, source_id, bank)
                    action, existing = check_duplicate(db, txn)

                    if action == "new":
                        _insert_transaction(db, txn)
                        account_inserted += 1
                    elif action == "pending_to_completed":
                        update_pending_to_completed(
                            db, existing["id"], txn["original_id"],
                            txn["processed_date"], txn["amount"],
                        )
                        account_updated += 1
                    else:
                        account_skipped += 1
                except Exception as e:
                    error_msg = f"Error processing txn: {e}"
                    result["errors"].append(error_msg)
                    print(f"  ERROR: {error_msg}")

            # Balance snapshot for bank accounts with balance data
            if source_type == "bank" and "balance" in account:
                _upsert_balance_snapshot(db, source_id, scrape_date, account["balance"])

            # Log scrape result
            total = account_inserted + account_updated + account_skipped
            _log_scrape(db, source_type, source_id, "success", total)

            result["inserted"] += account_inserted
            result["updated"] += account_updated
            result["skipped"] += account_skipped

            print(f"  {source_type}:{source_id} ({bank}/{account_number}): "
                  f"+{account_inserted} new, ~{account_updated} updated, ={account_skipped} skipped")

        db.commit()
    except Exception as e:
        result["errors"].append(str(e))
        print(f"  ERROR processing {file_path}: {e}")
    finally:
        if close_db:
            db.close()

    return result


def _latest_file_per_bank(output_dir: Path) -> list[Path]:
    """Find the most recent JSON file in each bank subdirectory."""
    files = []
    if not output_dir.exists():
        return files
    for bank_dir in sorted(output_dir.iterdir()):
        if not bank_dir.is_dir():
            continue
        json_files = sorted(bank_dir.glob("*.json"))
        if json_files:
            files.append(json_files[-1])
    return files


def ingest_all(output_dir: str | Path | None = None) -> list[dict]:
    """Find latest JSON file per bank and process each."""
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)

    files = _latest_file_per_bank(output_dir)
    if not files:
        print(f"No JSON files found in {output_dir}")
        return []

    results = []
    db = get_connection()
    try:
        for f in files:
            print(f"Processing {f.name}...")
            r = ingest_file(f, db=db)
            results.append(r)
    finally:
        db.close()

    # Summary
    total_inserted = sum(r["inserted"] for r in results)
    total_updated = sum(r["updated"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_errors = sum(len(r["errors"]) for r in results)
    print(f"\nDone: {total_inserted} inserted, {total_updated} updated, "
          f"{total_skipped} skipped, {total_errors} errors")

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ingest_file(sys.argv[1])
    else:
        ingest_all()
