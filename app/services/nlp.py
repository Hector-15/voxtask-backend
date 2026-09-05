"""
Natural-language interpretation for VoxTask.

Two paths:
  1. If ANTHROPIC_API_KEY is set -> call the LLM for interpretation.
  2. Otherwise -> deterministic rule-based Spanish parser (offline-friendly).

CRITICAL DESIGN RULE: all relative dates ("mañana", "el próximo viernes",
"dentro de tres horas") are resolved against the USER'S timezone and the
reference "now" the client provides, never against the server clock or the
model's imagination.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.schemas import InterpretResult

# ---- lookup tables -------------------------------------------------

WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 6, "domingo": 6,
}
# note: fix sábado index
WEEKDAYS["sabado"] = 5
WEEKDAYS["sábado"] = 5

NUM_WORDS = {
    "una": 1, "uno": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "quince": 15, "veinte": 20, "treinta": 30,
}

CATEGORY_HINTS = {
    "Trabajo": ["reunión", "reunion", "cotización", "cotizacion", "cliente",
                "proyecto", "informe", "oficina", "correo", "email"],
    "Casa": ["casa", "mercado", "comprar", "lavar", "cocinar", "limpieza"],
    "Personal": ["médico", "medico", "cita", "gimnasio", "banco", "pagar"],
    "Clientes": ["cliente", "propuesta", "factura"],
}

CONSULTA_TRIGGERS = ["qué tengo", "que tengo", "qué tareas", "que tareas",
                     "cuáles son", "cuales son", "muéstrame", "muestrame",
                     "pendiente", "vencidas", "esta semana"]


def _now(tz: str, client_now: datetime | None) -> datetime:
    zone = ZoneInfo(tz)
    if client_now is not None:
        if client_now.tzinfo is None:
            return client_now.replace(tzinfo=zone)
        return client_now.astimezone(zone)
    return datetime.now(zone)


def _extract_time(text: str, base: datetime) -> tuple[datetime | None, bool]:
    """Return (datetime with time set, found?). Handles am/pm and 'las N'."""
    t = text.lower()
    # "a las 8", "las 8:30", "a las 9 de la noche"
    m = re.search(r"(?:a\s+)?las?\s+(\d{1,2})(?::(\d{2}))?\s*"
                  r"(de la (mañana|tarde|noche)|a\.?\s*m\.?|p\.?\s*m\.?)?", t)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        suffix = m.group(3) or ""
        if "tarde" in suffix or "noche" in suffix or "p" in suffix:
            if hour < 12:
                hour += 12
        if ("mañana" in suffix or "a.m" in suffix or "am" in suffix) and hour == 12:
            hour = 0
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0), True

    # coarse dayparts
    if "esta noche" in t or "en la noche" in t:
        return base.replace(hour=20, minute=0, second=0, microsecond=0), True
    if "esta tarde" in t or "en la tarde" in t:
        return base.replace(hour=15, minute=0, second=0, microsecond=0), True
    if "en la mañana" in t or "por la mañana" in t:
        return base.replace(hour=9, minute=0, second=0, microsecond=0), True
    return None, False


def _extract_date(text: str, now: datetime) -> tuple[datetime | None, bool]:
    """Resolve a base DATE (time filled later). Returns (date-at-midnight, found)."""
    t = text.lower()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if "pasado mañana" in t:
        return midnight + timedelta(days=2), True
    if "mañana" in t:
        return midnight + timedelta(days=1), True
    if "hoy" in t or "esta noche" in t or "esta tarde" in t:
        return midnight, True

    # "dentro de N horas/días" / "en N horas/días"
    m = re.search(r"(?:dentro de|en)\s+([\w]+)\s+(hora|horas|día|dia|días|dias|"
                  r"semana|semanas|minuto|minutos)", t)
    if m:
        qty_raw = m.group(1)
        qty = int(qty_raw) if qty_raw.isdigit() else NUM_WORDS.get(qty_raw, 0)
        unit = m.group(2)
        if qty:
            if "hora" in unit:
                return now + timedelta(hours=qty), True
            if "minuto" in unit:
                return now + timedelta(minutes=qty), True
            if "semana" in unit:
                return midnight + timedelta(weeks=qty), True
            return midnight + timedelta(days=qty), True

    # "el próximo viernes" / "el viernes" / "todos los lunes"
    for name, idx in WEEKDAYS.items():
        if name in t:
            days_ahead = (idx - now.weekday()) % 7
            if days_ahead == 0 or "próximo" in t or "proximo" in t:
                days_ahead = days_ahead or 7
            return midnight + timedelta(days=days_ahead), True

    return None, False


def _extract_recurrence(text: str) -> str | None:
    t = text.lower()
    if "todos los días" in t or "todos los dias" in t or "diariamente" in t:
        return "FREQ=DAILY"
    for name, idx in WEEKDAYS.items():
        if f"todos los {name}" in t or f"cada {name}" in t:
            days = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"][idx]
            return f"FREQ=WEEKLY;BYDAY={days}"
    if "cada semana" in t or "semanalmente" in t:
        return "FREQ=WEEKLY"
    if "cada mes" in t or "mensualmente" in t:
        return "FREQ=MONTHLY"
    if "último viernes de cada mes" in t or "ultimo viernes de cada mes" in t:
        return "FREQ=MONTHLY;BYDAY=-1FR"
    if "cada año" in t or "anualmente" in t:
        return "FREQ=YEARLY"
    return None


def _extract_person(text: str) -> str | None:
    m = re.search(r"(?:a|con|para)\s+([A-ZÁÉÍÓÚ][a-záéíóúñ]+)", text)
    return m.group(1) if m else None


def _suggest_category(text: str) -> str | None:
    t = text.lower()
    for cat, words in CATEGORY_HINTS.items():
        if any(w in t for w in words):
            return cat
    return None


def _extract_priority(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["urgente", "importante", "prioridad alta", "ya"]):
        return "alta"
    if "sin prisa" in t or "cuando pueda" in t:
        return "baja"
    return "media"


def _clean_title(text: str) -> str:
    """Strip scheduling boilerplate to leave the action as the title."""
    t = text.strip()

    # Remove leading reminder verbs.
    t = re.sub(r"^(recuérdame|recuerdame|recordarme|recuérdame que|"
               r"anota|apunta|agenda|agéndame|necesito|tengo que)\s+",
               "", t, flags=re.I)

    # Cut everything from the first scheduling marker onward, so the action
    # + object survive but the date/time clause is dropped.
    markers = (
        r"\bpasado mañana\b", r"\bmañana\b", r"\bhoy\b",
        r"\besta noche\b", r"\besta tarde\b", r"\ben la (mañana|tarde|noche)\b",
        r"\ba las?\s+\d", r"\bel\s+(próximo|proximo)\b", r"\bel\s+lunes\b",
        r"\bel\s+martes\b", r"\bel\s+mi[eé]rcoles\b", r"\bel\s+jueves\b",
        r"\bel\s+viernes\b", r"\bel\s+s[aá]bado\b", r"\bel\s+domingo\b",
        r"\bdentro de\b", r"\ben \d+\b", r"\btodos los\b", r"\bcada\b",
        r"\bpara preguntarle\b", r"\bpara pedir\b",
    )
    before = t
    cut = len(t)
    for m in markers:
        found = re.search(m, t, flags=re.I)
        if found:
            cut = min(cut, found.start())
    head = t[:cut].strip(" .,")

    if not head:
        # Action verb comes AFTER the schedule clause (e.g.
        # "mañana a las 8 llamar a Juan"). Strip leading time/date tokens.
        tail = re.sub(
            r"^(mañana|hoy|pasado mañana|esta noche|esta tarde|"
            r"a las?\s+\d{1,2}(:\d{2})?|de la (mañana|tarde|noche)|"
            r"dentro de \w+ (horas?|d[ií]as?|minutos?)|en \d+ \w+|"
            r"el (próximo|proximo)?\s*\w+|y|,|\s)+",
            "", before, flags=re.I,
        )
        head = tail.strip(" .,")

    # Drop trailing "para preguntarle/pedir ..." purpose clauses.
    head = re.split(r"\s+para (preguntar|pedir|coordinar|revisar con)",
                    head, flags=re.I)[0].strip(" .,")

    head = re.sub(r"\s+", " ", head)
    return head[0].upper() + head[1:] if head else "Nueva tarea"


def _extract_followup(text: str, now: datetime) -> datetime | None:
    """Detect a conditional re-reminder clause and resolve its date.

    Matches phrases like:
      '... y si no lo completo, recuérdamelo el viernes'
      '... si no lo he marcado, avísame de nuevo mañana'
      '... recuérdamelo nuevamente el lunes si no lo hago'
    Returns the datetime of the re-reminder, or None.
    """
    t = text.lower()

    # Must contain a conditional-negation cue tied to completion.
    cond = re.search(
        r"si no (lo |la |me )?(he )?(complet|marc|hag|termin|llam|realiz)",
        t,
    )
    again = re.search(r"(nuevamente|de nuevo|otra vez|recu[eé]rda|av[ií]sa)", t)
    if not cond and not again:
        return None
    if not cond:
        return None

    # The re-reminder date is usually the LAST date expression in the phrase.
    # Take the text from the conditional cue onward and parse a date there;
    # if nothing, parse the whole sentence's last date.
    tail = text[cond.start():]
    followup, found = _extract_date(tail, now)
    if not found:
        followup, found = _extract_date(text, now)
    if not found or followup is None:
        return None

    # Attach a time if the tail specifies one; otherwise default to 9:00.
    ft, has_time = _extract_time(tail, followup)
    if has_time:
        return ft
    return followup.replace(hour=9, minute=0, second=0, microsecond=0)


def interpret_rule_based(text: str, tz: str, client_now: datetime | None) -> InterpretResult:
    now = _now(tz, client_now)
    lower = text.lower()

    # Is this a query rather than a task?
    if any(trig in lower for trig in CONSULTA_TRIGGERS) and not lower.startswith(
        ("recuérdame", "recuerdame", "anota", "agenda")
    ):
        return InterpretResult(intent="consultar", raw_text=text, title=text)

    # Split off the conditional follow-up clause so its date ("el viernes")
    # doesn't pollute the main task's date. Everything before "y si no…" is
    # the task; the follow-up is resolved from the tail.
    followup_at = _extract_followup(text, now)
    main_text = text
    split = re.search(r"\s+y?\s*si no\b", lower)
    if split:
        main_text = text[: split.start()]

    date_base, has_date = _extract_date(main_text, now)
    reference = date_base or now
    dt, has_time = _extract_time(main_text, reference)

    if has_time:
        due = dt
    elif has_date:
        due = date_base  # midnight of that day
    else:
        due = None

    missing = []
    if due is None:
        missing.append("fecha")
    elif not has_time and has_date and due.hour == 0:
        missing.append("hora")

    return InterpretResult(
        intent="crear_tarea",
        title=_clean_title(main_text),
        description="",
        due_at=due,
        category_suggestion=_suggest_category(main_text),
        priority=_extract_priority(main_text),
        person=_extract_person(main_text),
        recurrence_rule=_extract_recurrence(main_text),
        followup_at=followup_at,
        missing_fields=missing,
        raw_text=text,
    )


def interpret(text: str, tz: str, client_now: datetime | None) -> InterpretResult:
    """Entry point. LLM path can be added here; falls back to rules."""
    # LLM path intentionally deferred to keep MVP offline-capable and testable.
    # When ANTHROPIC_API_KEY is present, call the model here and merge results.
    return interpret_rule_based(text, tz, client_now)


# ------------------------------------------------------------------
# Voice search: parse a question into a structured query filter.
# ------------------------------------------------------------------

def parse_query(text: str, tz: str, client_now: datetime | None) -> dict:
    """Turn '¿qué tengo mañana?' / '¿tareas de Formas?' into a filter dict.

    Returns keys: scope, range_start, range_end, person, project, label.
    """
    now = _now(tz, client_now)
    t = text.lower()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

    q: dict = {
        "scope": "todas",
        "range_start": None,
        "range_end": None,
        "person": None,
        "project": None,
        "label": "tus tareas",
    }

    if "vencida" in t:
        q["scope"] = "vencidas"
        q["label"] = "vencidas"
    elif "hoy" in t:
        q["scope"] = "rango"
        q["range_start"] = midnight
        q["range_end"] = midnight + timedelta(days=1)
        q["label"] = "hoy"
    elif "mañana" in t:
        q["scope"] = "rango"
        q["range_start"] = midnight + timedelta(days=1)
        q["range_end"] = midnight + timedelta(days=2)
        q["label"] = "mañana"
    elif "esta semana" in t or "la semana" in t:
        q["scope"] = "rango"
        q["range_start"] = midnight
        q["range_end"] = midnight + timedelta(days=7)
        q["label"] = "esta semana"
    elif "pendiente" in t:
        q["scope"] = "pendientes"
        q["label"] = "pendientes"

    # "con Juan" / "de Juan"
    person = _extract_person(text)
    if person:
        q["person"] = person
        q["label"] = f"con {person}"

    # "de Formas" / "del proyecto Formas" / "cliente de Formas"
    m = re.search(r"(?:proyecto|cliente|de|del)\s+([A-ZÁÉÍÓÚ][\wáéíóúñ]+)", text)
    if m and (m.group(1) != person):
        cand = m.group(1)
        if cand.lower() not in WEEKDAYS and cand.lower() not in (
            "hoy", "mañana", "manana", "esta"
        ):
            q["project"] = cand
            q["label"] = f"de {cand}"

    return q
