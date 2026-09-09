from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import HunterFeedback, ManualHuntQueueItem
from app.db.session import get_db

router = APIRouter()


class FeedbackIn(BaseModel):
    manual_hunt_queue_item_id: str
    verdict: str  # interesting / noise / duplicate
    note: str | None = None


@router.post("")
def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_db)):
    """
    Per methodology section 14: every Interesting/Noise/Duplicate verdict
    you give feeds `scoring/target_scorer.recompute_weights_from_feedback`.
    Run that as a periodic offline job once you have enough rows (the
    function itself requires >=5 co-occurrences per signal before adjusting).
    """
    feedback = HunterFeedback(
        manual_hunt_queue_item_id=payload.manual_hunt_queue_item_id,
        verdict=payload.verdict,
        note=payload.note,
    )
    db.add(feedback)

    if payload.verdict in ("noise", "duplicate"):
        item = db.get(ManualHuntQueueItem, payload.manual_hunt_queue_item_id)
        if item:
            item.dismissed = True

    db.commit()
    return {"ok": True}
