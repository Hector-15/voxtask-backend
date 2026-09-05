from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    timezone: str = "America/Bogota"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    timezone: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- NLP ----------
class InterpretRequest(BaseModel):
    text: str
    # Client sends its local "now" so relative dates resolve correctly.
    client_now: Optional[datetime] = None


class InterpretResult(BaseModel):
    intent: str  # crear_tarea | consultar | seguimiento | desconocido
    title: Optional[str] = None
    description: Optional[str] = ""
    due_at: Optional[datetime] = None
    category_suggestion: Optional[str] = None
    priority: str = "media"
    person: Optional[str] = None
    recurrence_rule: Optional[str] = None
    followup_at: Optional[datetime] = None  # conditional re-reminder time
    missing_fields: List[str] = []
    raw_text: str = ""


# ---------- Voice search ----------
class QueryRequest(BaseModel):
    text: str
    client_now: Optional[datetime] = None


class QueryResponse(BaseModel):
    spoken: str  # natural-language answer to read aloud
    label: str  # e.g. "mañana", "con Juan"
    tasks: List["TaskOut"] = []


# ---------- Tasks ----------
class TaskCreate(BaseModel):
    title: str
    description: str = ""
    due_at: Optional[datetime] = None
    category_id: Optional[int] = None
    priority: str = "media"
    person: Optional[str] = None
    recurrence_rule: Optional[str] = None
    followup_at: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    category_id: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    due_at: Optional[datetime]
    category_id: Optional[int]
    priority: str
    person: Optional[str]
    status: str
    recurrence_rule: Optional[str]
    has_followup: bool = False

    class Config:
        from_attributes = True


# Resolve forward reference (QueryResponse -> TaskOut)
QueryResponse.model_rebuild()


# ---------- Categories ----------
class CategoryCreate(BaseModel):
    name: str
    color: str = "#4F46E5"


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str

    class Config:
        from_attributes = True


# ---------- History ----------
class HistoryOut(BaseModel):
    id: int
    task_id: Optional[int]
    action: str
    timestamp: datetime
    detail: str

    class Config:
        from_attributes = True
