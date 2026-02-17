import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.models import TransactionClassify, TransactionResponse, TransactionUpdate
from db.database import get_db

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    category: Optional[int] = Query(None),
    account: Optional[int] = Query(None),
    source_type: Optional[str] = Query(None),
    db: sqlite3.Connection = Depends(get_db),
):
    clauses = []
    params = []
    if from_date:
        clauses.append("date >= ?")
        params.append(from_date)
    if to_date:
        clauses.append("date <= ?")
        params.append(to_date)
    if category is not None:
        clauses.append("category_id = ?")
        params.append(category)
    if account is not None:
        clauses.append("source_type = 'bank' AND source_id = ?")
        params.append(account)
    if source_type:
        clauses.append("source_type = ?")
        params.append(source_type)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = db.execute(f"SELECT * FROM transactions{where} ORDER BY date DESC", params).fetchall()
    return [dict(r) for r in rows]


@router.get("/uncategorized", response_model=list[TransactionResponse])
def list_uncategorized(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM transactions WHERE category_id = 1 ORDER BY date DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")

    updates = []
    params = []
    if body.category_id is not None:
        updates.append("category_id = ?")
        params.append(body.category_id)
    if body.notes is not None:
        updates.append("notes = ?")
        params.append(body.notes)
    if body.amount is not None:
        updates.append("amount = ?")
        params.append(body.amount)

    if updates:
        params.append(transaction_id)
        db.execute(
            f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?", params
        )
        db.commit()

    row = db.execute(
        "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    return dict(row)


@router.put("/{transaction_id}/classify", response_model=TransactionResponse)
def classify_transaction(
    transaction_id: int,
    body: TransactionClassify,
    db: sqlite3.Connection = Depends(get_db),
):
    existing = db.execute(
        "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")

    cat = db.execute(
        "SELECT id FROM categories WHERE id = ?", (body.category_id,)
    ).fetchone()
    if not cat:
        raise HTTPException(status_code=400, detail="Category not found")

    db.execute(
        "UPDATE transactions SET category_id = ?, transaction_type = ? WHERE id = ?",
        (body.category_id, body.transaction_type, transaction_id),
    )

    if body.create_rule:
        keyword = body.keyword or existing["description"]
        db.execute(
            "INSERT INTO classification_rules (category_id, keyword, match_type) VALUES (?, ?, ?)",
            (body.category_id, keyword, body.match_type),
        )

    db.commit()

    row = db.execute(
        "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
    ).fetchone()
    return dict(row)
