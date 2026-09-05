from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)

c.post("/auth/register", json={"email":"b@t.com","password":"secret123","timezone":"America/Bogota"})
tok = c.post("/auth/login", data={"username":"b@t.com","password":"secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
now = "2026-09-04T10:00:00-05:00"

# Seed several tasks
seeds = [
    "Recuérdame mañana a las 8 llamar a Juan para la cotización",
    "Comprar mercado hoy a las 3 de la tarde",
    "Reunión con Juan el próximo viernes a las 9",
    "Revisar el diseño del cliente de Formas mañana a las 11",
    "Enviar informe hoy a las 5 de la tarde",
]
for s in seeds:
    d = c.post("/nlp/interpret", headers=H, json={"text":s,"client_now":now}).json()
    c.post("/tasks", headers=H, json={
        "title":d["title"],"description":d["description"],"due_at":d["due_at"],
        "priority":d["priority"],"person":d["person"]})

# Ask questions
questions = [
    "¿Qué tengo hoy?",
    "¿Qué tengo para mañana?",
    "¿Qué tareas tengo esta semana?",
    "¿Qué cosas tengo pendientes con Juan?",
    "¿Qué tareas tengo de Formas?",
    "¿Qué tareas vencidas tengo?",
]
for query in questions:
    r = c.post("/nlp/query", headers=H, json={"text":query,"client_now":now}).json()
    print(f"\nP: {query}")
    print(f"R: {r['spoken']}")
    print(f"   ({len(r['tasks'])} tarea(s), filtro='{r['label']}')")
