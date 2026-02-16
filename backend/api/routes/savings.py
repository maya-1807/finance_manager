import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import SavingsCreate, SavingsResponse
from db.database import get_db

router = APIRouter(prefix="/api/savings", tags=["savings"])

COLS = "id, name, account_id, initial_amount, current_amount, start_date, end_date, interest_rate"


@router.get("", response_model=list[SavingsResponse])
def list_savings(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(f"SELECT {COLS} FROM savings").fetchall()
    return [dict(r) for r in rows]


@router.get("/{savings_id}", response_model=SavingsResponse)
def get_savings(savings_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(f"SELECT {COLS} FROM savings WHERE id = ?", (savings_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Savings not found")
    return dict(row)


@router.post("", response_model=SavingsResponse, status_code=201)
def create_savings(body: SavingsCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO savings (name, account_id, initial_amount, current_amount, "
        "start_date, end_date, interest_rate) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (body.name, body.account_id, body.initial_amount, body.current_amount,
         body.start_date, body.end_date, body.interest_rate),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{savings_id}", response_model=SavingsResponse)
def update_savings(savings_id: int, body: SavingsCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM savings WHERE id = ?", (savings_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Savings not found")
    db.execute(
        "UPDATE savings SET name = ?, account_id = ?, initial_amount = ?, current_amount = ?, "
        "start_date = ?, end_date = ?, interest_rate = ? WHERE id = ?",
        (body.name, body.account_id, body.initial_amount, body.current_amount,
         body.start_date, body.end_date, body.interest_rate, savings_id),
    )
    db.commit()
    return {**body.model_dump(), "id": savings_id}


@router.delete("/{savings_id}", status_code=204)
def delete_savings(savings_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM savings WHERE id = ?", (savings_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Savings not found")
    db.execute("DELETE FROM savings WHERE id = ?", (savings_id,))
    db.commit()
