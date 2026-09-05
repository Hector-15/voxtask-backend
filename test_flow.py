from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

def show(label, r):
    print(f"\n=== {label} [{r.status_code}] ===")
    try: print(r.json())
    except: print(r.text)

# 1-2. Register
r = c.post("/auth/register", json={"email":"ana@test.com","password":"secret123","timezone":"America/Bogota"})
show("Registro", r)

# Login
r = c.post("/auth/login", data={"username":"ana@test.com","password":"secret123"})
show("Login", r)
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# Reference "now": Thursday 2026-09-04 10:00 Bogota
now = "2026-09-04T10:00:00-05:00"

# 3-9. Interpret several natural-language phrases
tests = [
    "Recuérdame mañana a las 8 llamar a Juan para preguntarle por la cotización",
    "Recuérdame llamar a Juan mañana",           # missing hora
    "Comprar mercado esta tarde",
    "Reunión con el cliente el próximo viernes a las 3 de la tarde",
    "Pagar la factura todos los lunes a las 9",
    "Dentro de tres horas revisar el correo",
]
for t in tests:
    r = c.post("/nlp/interpret", headers=H, json={"text":t,"client_now":now})
    d = r.json()
    print(f"\n>>> '{t}'")
    print(f"    intent={d['intent']} | title={d['title']!r} | due={d['due_at']} "
          f"| cat={d['category_suggestion']} | person={d['person']} "
          f"| rec={d['recurrence_rule']} | missing={d['missing_fields']}")

# 10-12. Confirm & save the first interpreted task
r = c.post("/nlp/interpret", headers=H, json={"text":tests[0],"client_now":now})
draft = r.json()
r = c.post("/tasks", headers=H, json={
    "title":draft["title"],"description":"Cotización cocina",
    "due_at":draft["due_at"],"priority":draft["priority"],"person":draft["person"]
})
show("Guardar tarea", r)
task_id = r.json()["id"]

# 16-17. Query today / upcoming
show("Hoy", c.get("/tasks/today", headers=H))
show("Próximas", c.get("/tasks/upcoming", headers=H))

# 15. Snooze then 14. Complete
show("Posponer 30min", c.post(f"/tasks/{task_id}/snooze?minutes=30", headers=H))
show("Completar", c.post(f"/tasks/{task_id}/complete", headers=H))

print("\n=== FLUJO MVP COMPLETO OK ===")
