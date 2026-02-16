import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import FixedIncomeCreate, FixedIncomeResponse
from db.database import get_db

router = APIRouter(prefix="/api/fixed-incomes", tags=["fixed incomes"])


@router.get("", response_model=list[FixedIncomeResponse])
def list_fixed_incomes(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM fixed_incomes").fetchall()
    return [dict(r) for r in rows]


@router.get("/{income_id}", response_model=FixedIncomeResponse)
def get_fixed_income(income_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM fixed_incomes WHERE id = ?", (income_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fixed income not found")
    return dict(row)


@router.post("", response_model=FixedIncomeResponse, status_code=201)
def create_fixed_income(body: FixedIncomeCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO fixed_incomes (name, expected_amount, frequency, account_id, day_of_month, keyword) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (body.name, body.expected_amount, body.frequency, body.account_id, body.day_of_month, body.keyword),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{income_id}", response_model=FixedIncomeResponse)
def update_fixed_income(income_id: int, body: FixedIncomeCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM fixed_incomes WHERE id = ?", (income_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Fixed income not found")
    db.execute(
        "UPDATE fixed_incomes SET name = ?, expected_amount = ?, frequency = ?, "
        "account_id = ?, day_of_month = ?, keyword = ? WHERE id = ?",
        (body.name, body.expected_amount, body.frequency, body.account_id, body.day_of_month, body.keyword, income_id),
    )
    db.commit()
    return {**body.model_dump(), "id": income_id}


@router.delete("/{income_id}", status_code=204)
def delete_fixed_income(income_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM fixed_incomes WHERE id = ?", (income_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Fixed income not found")
    db.execute("DELETE FROM fixed_incomes WHERE id = ?", (income_id,))
    db.commit()
