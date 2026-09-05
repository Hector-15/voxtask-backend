# Cómo desplegar el backend (para que la app funcione en cualquier lugar)

El backend es el "cerebro" que interpreta la voz. Desplegarlo en internet hace
que tu app funcione desde cualquier red, sin depender de tu computadora.

Te explico **dos opciones gratuitas**. Render es la más simple porque un solo
archivo (`render.yaml`) crea el servidor y la base de datos juntos.

---

## Antes de empezar

Sube la carpeta `voxtask-backend` a un repositorio de GitHub (puede ser el mismo
donde está la app, en otra carpeta, o uno separado). El proceso es igual que con
la app: **New repository** → subir archivos.

---

## OPCIÓN A — Render (recomendada)

1. Entra a https://render.com y regístrate (puedes usar tu cuenta de GitHub).
2. En el panel, haz clic en **New** → **Blueprint**.
3. Conecta tu repositorio de GitHub y elige el que tiene `voxtask-backend`.
4. Render detecta el archivo `render.yaml` y te muestra lo que va a crear:
   - un **servicio web** (el backend)
   - una **base de datos PostgreSQL** (plan gratuito)
5. Haz clic en **Apply**. Render construye e inicia todo (tarda unos minutos).
6. Cuando termine, tu backend tendrá una URL como
   `https://voxtask-backend.onrender.com`. Cópiala.

Para comprobar que vive: abre `https://TU-URL.onrender.com/health` en el
navegador. Debe responder `{"status":"ok",...}`.

> **Nota sobre el plan gratuito de Render:** el servidor "se duerme" tras 15
> minutos sin uso. La primera petición después de dormir tarda ~30–50 segundos
> en despertar; las siguientes son rápidas. Es normal en el plan gratis.

---

## OPCIÓN B — Railway

1. Entra a https://railway.app y regístrate con GitHub.
2. **New Project** → **Deploy from GitHub repo** → elige tu repo.
3. Railway detecta el `Procfile` y despliega el backend.
4. Añade la base de datos: en el proyecto, **New** → **Database** →
   **Add PostgreSQL**. Railway crea la variable `DATABASE_URL` y la conecta sola.
5. Genera la clave secreta: en el servicio, pestaña **Variables**, añade
   `SECRET_KEY` con un texto largo y aleatorio (puedes usar un generador de
   contraseñas).
6. En **Settings** → **Networking** → **Generate Domain** para obtener tu URL
   pública.

---

## Variables de entorno (ambas opciones)

| Variable | Para qué | ¿Obligatoria? |
|----------|----------|---------------|
| `DATABASE_URL` | Conexión a PostgreSQL | Sí (la crea el proveedor) |
| `SECRET_KEY` | Firma de los tokens de sesión | Sí (Render la genera; en Railway la pones tú) |
| `ANTHROPIC_API_KEY` | Usar el LLM para interpretar voz | No — sin ella usa el parser de reglas |
| `CORS_ORIGINS` | Orígenes permitidos | No — por defecto `*` |

---

## Paso final — Conectar la app al backend

1. Abre `voxtask-app/lib/services/api_service.dart`.
2. Cambia la línea del `baseUrl` por tu URL pública:
   ```dart
   static const String baseUrl = 'https://voxtask-backend.onrender.com';
   ```
3. Sube el cambio de la app a GitHub. GitHub Actions recompila el APK con la
   nueva dirección. Descarga el nuevo APK e instálalo.

¡Y listo! La app ya habla con tu backend en la nube desde cualquier red.

---

## Recomendaciones de seguridad para producción

- `SECRET_KEY` siempre desde variable de entorno, nunca en el código.
- Restringe `CORS_ORIGINS` si tienes una web (para la app móvil `*` está bien).
- La base de datos gratuita tiene límites de tamaño; para uso serio, sube de plan.
- Para que los **seguimientos condicionales** lleguen aunque nadie abra la app,
  configura una tarea programada (cron) que llame a `POST /tasks/process-followups`.
  Render y Railway ofrecen "cron jobs"; también sirve un servicio externo como
  cron-job.org apuntando a ese endpoint.
