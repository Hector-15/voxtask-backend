from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    timezone = Column(String, default="America/Bogota", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    tasks = relationship(
        "Task", back_populates="user", cascade="all, delete-orphan"
    )
    categories = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    color = Column(String, default="#4F46E5")

    user = relationship("User", back_populates="categories")
    tasks = relationship("Task", back_populates="category")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    due_at = Column(DateTime(timezone=True), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    priority = Column(String, default="media")  # baja | media | alta
    person = Column(String, nullable=True)
    status = Column(String, default="pendiente")  # pendiente|completada|pospuesta
    recurrence_rule = Column(String, nullable=True)  # RRULE string
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="tasks")
    category = relationship("Category", back_populates="tasks")
    reminders = relationship(
        "Reminder", back_populates="task", cascade="all, delete-orphan"
    )


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    fire_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="programado")  # programado|enviado|cancelado

    task = relationship("Task", back_populates="reminders")


class HistoryEntry(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)  # creada|modificada|completada|...
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    detail = Column(Text, default="")


class FollowUp(Base):
    """A conditional reminder: 'if the task isn't done by X, remind again at Y'.

    check_at is when we evaluate the condition. If the task is still pending
    at that moment, we fire a fresh reminder and mark this follow-up done.
    """
    __tablename__ = "followups"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    check_at = Column(DateTime(timezone=True), nullable=False)
    condition = Column(String, default="si_no_completada")  # extensible
    status = Column(String, default="pendiente")  # pendiente|disparado|cancelado
    created_at = Column(DateTime(timezone=True), default=utcnow)

    task = relationship("Task")
