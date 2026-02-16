import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import CreditCardCreate, CreditCardResponse
from db.database import get_db

router = APIRouter(prefix="/api/credit-cards", tags=["credit cards"])

COLS = "id, account_id, name, company, last_4_digits, billing_day, scraper_type"


@router.get("", response_model=list[CreditCardResponse])
def list_credit_cards(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(f"SELECT {COLS} FROM credit_cards").fetchall()
    return [dict(r) for r in rows]


@router.get("/{card_id}", response_model=CreditCardResponse)
def get_credit_card(card_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(f"SELECT {COLS} FROM credit_cards WHERE id = ?", (card_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Credit card not found")
    return dict(row)


@router.post("", response_model=CreditCardResponse, status_code=201)
def create_credit_card(body: CreditCardCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO credit_cards (account_id, name, company, last_4_digits, billing_day, scraper_type) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (body.account_id, body.name, body.company, body.last_4_digits, body.billing_day, body.scraper_type),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{card_id}", response_model=CreditCardResponse)
def update_credit_card(card_id: int, body: CreditCardCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM credit_cards WHERE id = ?", (card_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Credit card not found")
    db.execute(
        "UPDATE credit_cards SET account_id = ?, name = ?, company = ?, last_4_digits = ?, "
        "billing_day = ?, scraper_type = ? WHERE id = ?",
        (body.account_id, body.name, body.company, body.last_4_digits, body.billing_day, body.scraper_type, card_id),
    )
    db.commit()
    return {**body.model_dump(), "id": card_id}


@router.delete("/{card_id}", status_code=204)
def delete_credit_card(card_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM credit_cards WHERE id = ?", (card_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Credit card not found")

    # transactions use source_type/source_id, not credit_card_id
    count = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE source_type = 'credit_card' AND source_id = ?",
        (card_id,),
    ).fetchone()[0]
    if count > 0:
        raise HTTPException(status_code=409, detail="Cannot delete credit card: referenced by transactions")

    count = db.execute(
        "SELECT COUNT(*) FROM fixed_expenses WHERE credit_card_id = ?", (card_id,)
    ).fetchone()[0]
    if count > 0:
        raise HTTPException(status_code=409, detail="Cannot delete credit card: referenced by fixed_expenses")

    db.execute("DELETE FROM credit_cards WHERE id = ?", (card_id,))
    db.commit()
