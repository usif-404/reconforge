from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Endpoint, Program
from app.db.session import get_db

router = APIRouter()


@router.get("/top-targets")
def top_targets(program_name: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    """
    "TOP TARGETS TODAY" dashboard from methodology section 11 — every
    discovered endpoint's `score` column, ranked, is exactly this query.
    """
    stmt = select(Endpoint).order_by(Endpoint.score.desc()).limit(limit)
    if program_name:
        program = db.scalar(select(Program).where(Program.name == program_name))
        if not program:
            return {"error": "program not found"}
        stmt = stmt.where(Endpoint.program_id == program.id)

    endpoints = db.scalars(stmt).all()
    return [
        {"path": e.path_template, "method": e.method, "category": e.category, "score": e.score}
        for e in endpoints
    ]
