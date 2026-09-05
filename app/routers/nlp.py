from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import Category, Task, User
from app.models.schemas import (
    InterpretRequest,
    InterpretResult,
    QueryRequest,
    QueryResponse,
    TaskOut,
)
from app.services.date_speech import speak_answer
from app.services.nlp import interpret, parse_query

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.post("/interpret", response_model=InterpretResult)
def interpret_text(
    req: InterpretRequest, user: User = Depends(get_current_user)
):
    """Turn a natural-language utterance into a structured task draft.

    The client shows this as an editable confirmation card before saving.
    """
    return interpret(req.text, user.timezone, req.client_now)


@router.post("/query", response_model=QueryResponse)
def voice_query(
    req: QueryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Answer a spoken question like '¿qué tengo mañana?' or
    '¿qué tareas tengo con Juan?' by filtering the user's tasks."""
    f = parse_query(req.text, user.timezone, req.client_now)
    tz = ZoneInfo(user.timezone)
    now = datetime.now(tz)

    q = db.query(Task).filter(
        Task.user_id == user.id, Task.status == "pendiente"
    )

    if f["scope"] == "vencidas":
        q = q.filter(Task.due_at < now)
    elif f["scope"] == "rango":
        if f["range_start"]:
            q = q.filter(Task.due_at >= f["range_start"])
        if f["range_end"]:
            q = q.filter(Task.due_at < f["range_end"])

    if f["person"]:
        q = q.filter(Task.person.ilike(f"%{f['person']}%"))

    if f["project"]:
        cat = (
            db.query(Category)
            .filter(
                Category.user_id == user.id,
                Category.name.ilike(f"%{f['project']}%"),
            )
            .first()
        )
        proj = f["project"]
        if cat:
            q = q.filter(Task.category_id == cat.id)
        else:
            q = q.filter(
                (Task.title.ilike(f"%{proj}%"))
                | (Task.description.ilike(f"%{proj}%"))
            )

    tasks = q.order_by(Task.due_at.is_(None), Task.due_at).all()
    spoken = speak_answer(f["label"], tasks, user.timezone)
    return QueryResponse(
        spoken=spoken,
        label=f["label"],
        tasks=[TaskOut.model_validate(t) for t in tasks],
    )
