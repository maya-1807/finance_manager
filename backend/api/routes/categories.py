import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import CategoryCreate, CategoryResponse
from db.database import get_db

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM categories").fetchall()
    return [dict(r) for r in rows]


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    return dict(row)


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(body: CategoryCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO categories (name, monthly_budget, icon, color) VALUES (?, ?, ?, ?)",
        (body.name, body.monthly_budget, body.icon, body.color),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, body: CategoryCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    db.execute(
        "UPDATE categories SET name = ?, monthly_budget = ?, icon = ?, color = ? WHERE id = ?",
        (body.name, body.monthly_budget, body.icon, body.color, category_id),
    )
    db.commit()
    return {**body.model_dump(), "id": category_id}


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: sqlite3.Connection = Depends(get_db)):
    if category_id == 1:
        raise HTTPException(status_code=409, detail="Cannot delete the Uncategorized category")

    existing = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    for table, col in [("transactions", "category_id"), ("classification_rules", "category_id")]:
        count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} = ?", (category_id,)).fetchone()[0]
        if count > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete category: referenced by {table}",
            )

    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()
