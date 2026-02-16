import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import FixedExpenseCreate, FixedExpenseResponse
from db.database import get_db

router = APIRouter(prefix="/api/fixed-expenses", tags=["fixed expenses"])

COLS = ("id, name, expected_amount, frequency, payment_method, "
        "credit_card_id, account_id, keyword, day_of_month")


@router.get("", response_model=list[FixedExpenseResponse])
def list_fixed_expenses(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(f"SELECT {COLS} FROM fixed_expenses").fetchall()
    return [dict(r) for r in rows]


@router.get("/{expense_id}", response_model=FixedExpenseResponse)
def get_fixed_expense(expense_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(f"SELECT {COLS} FROM fixed_expenses WHERE id = ?", (expense_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fixed expense not found")
    return dict(row)


@router.post("", response_model=FixedExpenseResponse, status_code=201)
def create_fixed_expense(body: FixedExpenseCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO fixed_expenses (name, expected_amount, frequency, payment_method, "
        "credit_card_id, account_id, keyword, day_of_month) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (body.name, body.expected_amount, body.frequency, body.payment_method,
         body.credit_card_id, body.account_id, body.keyword, body.day_of_month),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{expense_id}", response_model=FixedExpenseResponse)
def update_fixed_expense(expense_id: int, body: FixedExpenseCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM fixed_expenses WHERE id = ?", (expense_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Fixed expense not found")
    db.execute(
        "UPDATE fixed_expenses SET name = ?, expected_amount = ?, frequency = ?, payment_method = ?, "
        "credit_card_id = ?, account_id = ?, keyword = ?, day_of_month = ? WHERE id = ?",
        (body.name, body.expected_amount, body.frequency, body.payment_method,
         body.credit_card_id, body.account_id, body.keyword, body.day_of_month, expense_id),
    )
    db.commit()
    return {**body.model_dump(), "id": expense_id}


@router.delete("/{expense_id}", status_code=204)
def delete_fixed_expense(expense_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM fixed_expenses WHERE id = ?", (expense_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Fixed expense not found")
    db.execute("DELETE FROM fixed_expenses WHERE id = ?", (expense_id,))
    db.commit()
