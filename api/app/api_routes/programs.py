from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Program
from app.db.session import get_db

router = APIRouter()


class ProgramOut(BaseModel):
    id: str
    name: str
    platform: str | None
    active: bool
    score: int

    class Config:
        from_attributes = True


@router.get("", response_model=list[ProgramOut])
def list_programs(db: Session = Depends(get_db)):
    programs = db.scalars(select(Program).order_by(Program.score.desc())).all()
    return [
        ProgramOut(id=str(p.id), name=p.name, platform=p.platform, active=p.active, score=p.score)
        for p in programs
    ]


@router.get("/{program_name}/changes")
def program_changes(program_name: str, hours: int = 24, db: Session = Depends(get_db)):
    from app.changes.detector import changes_since

    program = db.scalar(select(Program).where(Program.name == program_name))
    if not program:
        return {"error": "program not found"}

    changes = changes_since(db, program.id, hours=hours)
    return [
        {
            "change_type": c.change_type.value,
            "subject": c.subject,
            "detail": c.detail,
            "detected_at": c.detected_at.isoformat(),
        }
        for c in changes
    ]
