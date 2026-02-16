import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from api.models import ClassificationRuleCreate, ClassificationRuleResponse
from db.database import get_db

router = APIRouter(prefix="/api/classification-rules", tags=["classification rules"])


@router.get("", response_model=list[ClassificationRuleResponse])
def list_rules(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM classification_rules").fetchall()
    return [dict(r) for r in rows]


@router.get("/{rule_id}", response_model=ClassificationRuleResponse)
def get_rule(rule_id: int, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM classification_rules WHERE id = ?", (rule_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Classification rule not found")
    return dict(row)


@router.post("", response_model=ClassificationRuleResponse, status_code=201)
def create_rule(body: ClassificationRuleCreate, db: sqlite3.Connection = Depends(get_db)):
    cur = db.execute(
        "INSERT INTO classification_rules (category_id, keyword, match_type) VALUES (?, ?, ?)",
        (body.category_id, body.keyword, body.match_type),
    )
    db.commit()
    return {**body.model_dump(), "id": cur.lastrowid}


@router.put("/{rule_id}", response_model=ClassificationRuleResponse)
def update_rule(rule_id: int, body: ClassificationRuleCreate, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM classification_rules WHERE id = ?", (rule_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Classification rule not found")
    db.execute(
        "UPDATE classification_rules SET category_id = ?, keyword = ?, match_type = ? WHERE id = ?",
        (body.category_id, body.keyword, body.match_type, rule_id),
    )
    db.commit()
    return {**body.model_dump(), "id": rule_id}


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: sqlite3.Connection = Depends(get_db)):
    existing = db.execute("SELECT id FROM classification_rules WHERE id = ?", (rule_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Classification rule not found")
    db.execute("DELETE FROM classification_rules WHERE id = ?", (rule_id,))
    db.commit()
