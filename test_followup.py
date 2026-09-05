from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)

c.post("/auth/register", json={"email":"f@t.com","password":"secret123","timezone":"America/Bogota"})
tok = c.post("/auth/login", data={"username":"f@t.com","password":"secret123"}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
now = "2026-09-04T10:00:00-05:00"  # jueves

phrase = "Recuérdame llamar a Juan mañana a las 9 y si no lo completo, recuérdamelo el viernes"
d = c.post("/nlp/interpret", headers=H, json={"text":phrase,"client_now":now}).json()
print("=== Interpretación ===")
print(f"  título:    {d['title']!r}")
print(f"  tarea due: {d['due_at']}  (debe ser viernes 5 sep 9:00)")
print(f"  followup:  {d['followup_at']}  (debe ser viernes... espera, 'el viernes' desde jueves)")
print(f"  persona:   {d['person']}")

# Crear la tarea con el seguimiento
r = c.post("/tasks", headers=H, json={
    "title":d["title"],"due_at":d["due_at"],"person":d["person"],
    "followup_at":d["followup_at"]}).json()
print(f"\n=== Tarea creada id={r['id']} · has_followup={r['has_followup']} ===")
tid = r["id"]

# CASO A: la tarea NO se completa, y el check_at ya pasó -> debe dispararse
# Forzamos el check_at al pasado editando la BD directamente
import sqlite3
con = sqlite3.connect("voxtask.db")
con.execute("UPDATE followups SET check_at = ?", ("2026-09-04 08:00:00",))
con.commit(); con.close()

fired = c.post("/tasks/process-followups", headers=H).json()
print(f"\n=== CASO A (no completada) ===")
print(f"  seguimientos disparados: {len(fired)}")
for t in fired: print(f"    -> re-recordar: {t['title']}")

# CASO B: nueva tarea, se completa antes -> el seguimiento se cancela
d2 = c.post("/nlp/interpret", headers=H, json={"text":phrase,"client_now":now}).json()
r2 = c.post("/tasks", headers=H, json={
    "title":d2["title"],"due_at":d2["due_at"],"followup_at":d2["followup_at"]}).json()
tid2 = r2["id"]
comp = c.post(f"/tasks/{tid2}/complete", headers=H).json()
print(f"\n=== CASO B (completada antes) ===")
print(f"  tarea completada · has_followup ahora: {comp['has_followup']} (debe ser False)")

import sqlite3
con = sqlite3.connect("voxtask.db")
rows = list(con.execute("SELECT task_id, status FROM followups ORDER BY id"))
print(f"  estado seguimientos en BD: {rows}")
con.close()
