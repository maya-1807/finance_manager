import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import AccountCreate, AccountResponse
from db.database import get_db

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
def list_accounts(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM accounts").fetchall()
    return [dict(r) for r in rows]


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    return dict(row)


@router.post("", response_model=AccountResponse, status_code=201)
def create_account(body: AccountCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO accounts (name, bank, type, scraper_type) VALUES (?, ?, ?, ?)",
        (body.name, body.bank, body.type, body.scraper_type),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, body: AccountCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")
    db.execute(
        "UPDATE accounts SET name = ?, bank = ?, type = ?, scraper_type = ? WHERE id = ?",
        (body.name, body.bank, body.type, body.scraper_type, account_id),
    )
    db.commit()
    return {**body.model_dump(), "id": account_id}


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check references from tables with account_id FK
    for table in ("credit_cards", "fixed_incomes", "fixed_expenses", "savings", "balance_snapshots"):
        count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE account_id = ?", (account_id,)).fetchone()[0]
        if count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete account: referenced by {table}",
            )

    # transactions use source_type/source_id
    count = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE source_type = 'bank' AND source_id = ?",
        (account_id,),
    ).fetchone()[0]
    if count > 0:
        raise HTTPException(status_code=409, detail="Cannot delete account: referenced by transactions")

    db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    db.commit()
