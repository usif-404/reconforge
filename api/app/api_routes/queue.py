from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ManualHuntQueueItem
from app.db.session import get_db

router = APIRouter()


@router.get("")
def get_queue(dismissed: bool = False, limit: int = 50, db: Session = Depends(get_db)):
    stmt = (
        select(ManualHuntQueueItem)
        .where(ManualHuntQueueItem.dismissed == dismissed)
        .order_by(ManualHuntQueueItem.score.desc())
        .limit(limit)
    )
    items = db.scalars(stmt).all()
    return [
        {
            "id": str(i.id),
            "subject": i.subject,
            "score": i.score,
            "reason": i.reason,
            "created_at": i.created_at.isoformat(),
        }
        for i in items
    ]


@router.post("/{item_id}/dismiss")
def dismiss_item(item_id: str, db: Session = Depends(get_db)):
    item = db.get(ManualHuntQueueItem, item_id)
    if not item:
        return {"error": "not found"}
    item.dismissed = True
    db.commit()
    return {"ok": True}
