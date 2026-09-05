from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import HistoryEntry, User
from app.models.schemas import HistoryOut

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryOut])
def list_history(
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recent activity: tasks created, modified, completed, deleted,
    reminders sent, follow-ups triggered."""
    return (
        db.query(HistoryEntry)
        .filter(HistoryEntry.user_id == user.id)
        .order_by(HistoryEntry.timestamp.desc())
        .limit(min(limit, 200))
        .all()
    )
