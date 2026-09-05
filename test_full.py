from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
now = "2026-09-04T10:00:00-05:00"

# Full lifecycle
c.post("/auth/register", json={"email":"z@t.com","password":"secret123","timezone":"America/Bogota"})
tok=c.post("/auth/login",data={"username":"z@t.com","password":"secret123"}).json()["access_token"]
H={"Authorization":f"Bearer {tok}"}

ok=0; fail=0
def check(name, cond):
    global ok,fail
    print(f"  {'✓' if cond else '✗'} {name}"); 
    ok+=cond; fail+=(not cond)

print("AUTH & SETUP")
check("categorías por defecto", len(c.get("/categories",headers=H).json())==4)

print("VOZ → TAREA")
d=c.post("/nlp/interpret",headers=H,json={"text":"Recuérdame mañana a las 8 llamar a Juan para la cotización","client_now":now}).json()
check("interpreta título", "Llamar a Juan" in d["title"])
check("interpreta fecha", d["due_at"]=="2026-09-05T08:00:00-05:00")
t=c.post("/tasks",headers=H,json={"title":d["title"],"due_at":d["due_at"],"person":d["person"]}).json()
check("guarda tarea", t["id"]>0)

print("SEGUIMIENTO CONDICIONAL")
d2=c.post("/nlp/interpret",headers=H,json={"text":"Llamar a Ana hoy a las 3 de la tarde y si no lo completo recuérdamelo mañana","client_now":now}).json()
check("detecta seguimiento", d2["followup_at"] is not None)
t2=c.post("/tasks",headers=H,json={"title":d2["title"],"due_at":d2["due_at"],"followup_at":d2["followup_at"]}).json()
check("tarea con seguimiento", t2["has_followup"]==True)

print("MANUAL")
tm=c.post("/tasks",headers=H,json={"title":"Manual","due_at":"2026-09-05T12:00:00","priority":"alta"}).json()
check("crea manual", tm["priority"]=="alta")
c.patch(f"/tasks/{tm['id']}",headers=H,json={"priority":"baja"})
check("edita", c.get("/tasks",headers=H).json() is not None)

print("CONSULTA POR VOZ")
r=c.post("/nlp/query",headers=H,json={"text":"¿qué tengo mañana?","client_now":now}).json()
check("responde consulta", "mañana" in r["spoken"])

print("ACCIONES")
check("completar", c.post(f"/tasks/{t['id']}/complete",headers=H).json()["status"]=="completada")
check("posponer", c.post(f"/tasks/{tm['id']}/snooze?minutes=30",headers=H).status_code==200)

print("HISTORIAL")
h=c.get("/history",headers=H).json()
check("registra actividad", len(h)>=5)

print(f"\n=== {ok} OK / {fail} fallos ===")
