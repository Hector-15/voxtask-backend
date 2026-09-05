from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.models import FollowUp, HistoryEntry, Reminder, Task, User
from app.models.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _log(db, user_id, task_id, action, detail=""):
    db.add(HistoryEntry(user_id=user_id, task_id=task_id, action=action, detail=detail))


def _schedule_reminder(db, task: Task):
    if task.due_at:
        db.add(Reminder(task_id=task.id, fire_at=task.due_at, status="programado"))


def _out(task: Task, db: Session) -> TaskOut:
    """Serialize a task, flagging whether it has a pending follow-up."""
    has = (
        db.query(FollowUp)
        .filter(FollowUp.task_id == task.id, FollowUp.status == "pendiente")
        .first()
        is not None
    )
    data = TaskOut.model_validate(task)
    return data.model_copy(update={"has_followup": has})


@router.post("", response_model=TaskOut, status_code=201)
def create_task(
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = data.model_dump()
    followup_at = payload.pop("followup_at", None)
    task = Task(user_id=user.id, **payload)
    db.add(task)
    db.commit()
    db.refresh(task)
    _schedule_reminder(db, task)
    _log(db, user.id, task.id, "creada", task.title)
    if followup_at:
        db.add(FollowUp(task_id=task.id, check_at=followup_at))
        _log(db, user.id, task.id, "seguimiento_programado",
             followup_at.isoformat())
    db.commit()
    return _out(task, db)


@router.get("", response_model=list[TaskOut])
def list_tasks(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Task).filter(Task.user_id == user.id)
    if status:
        q = q.filter(Task.status == status)
    return q.order_by(Task.due_at.is_(None), Task.due_at).all()


@router.get("/today", response_model=list[TaskOut])
def tasks_today(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    tz = ZoneInfo(user.timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.due_at >= start,
            Task.due_at < end,
            Task.status == "pendiente",
        )
        .order_by(Task.due_at)
        .all()
    )


@router.get("/upcoming", response_model=list[TaskOut])
def tasks_upcoming(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tz = ZoneInfo(user.timezone)
    now = datetime.now(tz)
    end = now + timedelta(days=days)
    return (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.due_at > now,
            Task.due_at <= end,
            Task.status == "pendiente",
        )
        .order_by(Task.due_at)
        .all()
    )


@router.get("/overdue", response_model=list[TaskOut])
def tasks_overdue(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    tz = ZoneInfo(user.timezone)
    now = datetime.now(tz)
    return (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.due_at < now,
            Task.status == "pendiente",
        )
        .order_by(Task.due_at)
        .all()
    )


def _get_owned_task(db, user, task_id) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.user_id == user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, user, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    _log(db, user.id, task.id, "modificada")
    db.commit()
    db.refresh(task)
    return _out(task, db)


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, user, task_id)
    task.status = "completada"
    for r in task.reminders:
        if r.status == "programado":
            r.status = "cancelado"
    # No need to nag anymore — cancel any pending follow-ups.
    for fu in db.query(FollowUp).filter(
        FollowUp.task_id == task.id, FollowUp.status == "pendiente"
    ):
        fu.status = "cancelado"
    _log(db, user.id, task.id, "completada")
    db.commit()
    db.refresh(task)
    return _out(task, db)


@router.post("/{task_id}/snooze", response_model=TaskOut)
def snooze_task(
    task_id: int,
    minutes: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, user, task_id)
    tz = ZoneInfo(user.timezone)
    new_time = datetime.now(tz) + timedelta(minutes=minutes)
    task.due_at = new_time
    task.status = "pendiente"
    db.add(Reminder(task_id=task.id, fire_at=new_time, status="programado"))
    _log(db, user.id, task.id, "pospuesta", f"+{minutes}min")
    db.commit()
    db.refresh(task)
    return _out(task, db)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _get_owned_task(db, user, task_id)
    _log(db, user.id, task.id, "eliminada", task.title)
    db.delete(task)
    db.commit()


@router.post("/process-followups", response_model=list[TaskOut])
def process_followups(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Evaluate due follow-ups. For each one whose check_at has passed while
    the task is still pending, fire a fresh reminder and mark it triggered.

    Called by the app on launch (and ideally a server-side scheduler).
    Returns the tasks that got re-reminded so the app can notify.
    """
    tz = ZoneInfo(user.timezone)
    now = datetime.now(tz)
    retriggered: list[Task] = []

    due = (
        db.query(FollowUp)
        .join(Task, FollowUp.task_id == Task.id)
        .filter(
            Task.user_id == user.id,
            FollowUp.status == "pendiente",
            FollowUp.check_at <= now,
        )
        .all()
    )
    for fu in due:
        task = db.query(Task).filter(Task.id == fu.task_id).first()
        if task and task.status == "pendiente":
            # Still not done -> nag again at the follow-up time.
            task.due_at = fu.check_at
            db.add(Reminder(task_id=task.id, fire_at=fu.check_at,
                            status="programado"))
            _log(db, user.id, task.id, "seguimiento_disparado")
            retriggered.append(task)
        fu.status = "disparado"

    db.commit()
    return [_out(t, db) for t in retriggered]
