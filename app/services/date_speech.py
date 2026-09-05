"""Builds a natural Spanish sentence to read aloud in response to a query."""
from datetime import datetime
from zoneinfo import ZoneInfo

MONTHS = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _time_phrase(dt: datetime) -> str:
    if dt.hour == 0 and dt.minute == 0:
        return ""
    h = dt.hour
    suffix = "de la mañana"
    if 12 <= h < 19:
        suffix = "de la tarde"
    elif h >= 19 or h < 5:
        suffix = "de la noche"
    h12 = h % 12 or 12
    mins = f" y {dt.minute}" if dt.minute else ""
    return f" a las {h12}{mins} {suffix}"


def speak_answer(label: str, tasks: list, tz: str) -> str:
    n = len(tasks)
    if n == 0:
        return f"No tienes tareas {label}."

    if n == 1:
        t = tasks[0]
        when = ""
        if t.due_at:
            # Stored datetimes are already in the user's local time.
            # If tz-aware, convert; if naive, use as-is (already local).
            local = (
                t.due_at.astimezone(ZoneInfo(tz))
                if t.due_at.tzinfo is not None
                else t.due_at
            )
            when = _time_phrase(local)
        return f"Tienes una tarea {label}: {t.title}{when}."

    # Multiple: give the count, then list up to 3 titles.
    intro = f"Tienes {n} tareas {label}. "
    names = [t.title for t in tasks[:3]]
    if n <= 3:
        listing = ", ".join(names[:-1]) + f" y {names[-1]}"
    else:
        listing = ", ".join(names) + f", y {n - 3} más"
    return intro + listing + "."
