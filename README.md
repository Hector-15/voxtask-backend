# VoxTask — Backend MVP

Asistente de tareas y recordatorios controlado por voz y lenguaje natural.
Este es el **backend** (FastAPI): el cerebro que interpreta el lenguaje natural
y expone el contrato JSON que consumirá la app móvil Flutter.

## Qué incluye este MVP

Cubre los 17 pasos del MVP definido en el diseño, del lado servidor:

| # | Paso | Endpoint |
|---|------|----------|
| 1 | Crear cuenta | `POST /auth/register` |
| — | Iniciar sesión | `POST /auth/login` |
| 5-9 | Interpretar voz→texto con IA (tarea, fecha, hora, categoría, persona, recurrencia) | `POST /nlp/interpret` |
| + | Búsqueda por voz ("¿qué tengo mañana?") | `POST /nlp/query` |
| + | Seguimientos condicionales ("si no lo completo, recuérdamelo el viernes") | `POST /tasks/process-followups` |
| 10-11 | Confirmar y guardar | `POST /tasks` |
| 12 | Programar recordatorio | (automático al crear) |
| 14 | Completar tarea | `POST /tasks/{id}/complete` |
| 15 | Posponer tarea | `POST /tasks/{id}/snooze?minutes=N` |
| 16 | Consultar tareas de hoy | `GET /tasks/today` |
| 17 | Consultar próximas | `GET /tasks/upcoming` |
| — | Vencidas | `GET /tasks/overdue` |
| — | Eliminar cuenta y datos | `DELETE /auth/me` |

Los pasos 2-4 (permisos, grabación, captura del micrófono) y 13 (mostrar la
notificación) viven en la app móvil, no en el backend.

## Motor de lenguaje natural

`app/services/nlp.py` interpreta español y **resuelve fechas relativas en la
zona horaria del usuario**. Reconoce, entre otras:

- `mañana`, `hoy`, `pasado mañana`, `esta tarde`, `esta noche`
- `el próximo viernes`, `el lunes`
- `dentro de tres horas`, `en quince días`
- `a las 8`, `a las 3 de la tarde`, `a las 9 de la noche`
- recurrencia: `todos los lunes`, `cada mes`, `el último viernes de cada mes`
- categoría sugerida, persona relacionada y prioridad

Devuelve `missing_fields` (p. ej. `["hora"]`) para que la app dispare la
**pregunta conversacional** ("¿A qué hora?") antes de guardar.

### Seguimientos condicionales

Frases como *"llamar a Juan mañana y si no lo completo, recuérdamelo el viernes"*
se parten en dos: la tarea (antes de "y si no…") y el seguimiento (la fecha del
re-recordatorio). Se guarda un `FollowUp` con `check_at`. Al llamar
`POST /tasks/process-followups` (la app lo hace al abrir, e idealmente un cron en
el servidor), se evalúa: si la tarea sigue pendiente en esa fecha, se dispara un
nuevo recordatorio; si ya se completó, el seguimiento se cancela solo.

### Dos modos de interpretación- **Sin API key** (por defecto): parser de reglas determinista, funciona sin
  internet. Ideal para desarrollo, pruebas y como fallback offline.
- **Con `ANTHROPIC_API_KEY`**: el gancho en `interpret()` puede llamar al LLM
  para mayor cobertura. La resolución final de fechas sigue haciéndose en
  servidor con la zona horaria del usuario.

## Cómo ejecutar

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Documentación interactiva en `http://localhost:8000/docs`.

## Probar el flujo completo

```bash
python test_flow.py
```

Recorre: registro → login → interpretación de 6 frases → guardar → consultar
hoy/próximas → posponer → completar.

## Seguridad

- Contraseñas con bcrypt.
- JWT de acceso (30 min) + refresh (30 días).
- Aislamiento por usuario en cada consulta.
- Borrado de cuenta con cascada a tareas, categorías y recordatorios.
- Antes de producción: mover `SECRET_KEY` a variable de entorno, restringir CORS
  y migrar de SQLite a PostgreSQL (basta cambiar `DATABASE_URL`).

## Siguiente paso

App Flutter: pantalla principal (Hoy/Próximas/Vencidas) + botón de micrófono
que consume `POST /nlp/interpret` y muestra la tarjeta de confirmación editable.
