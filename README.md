# VoxTask — App Flutter (MVP)

App móvil del asistente de tareas por voz. Consume el backend FastAPI.

## Concepto visual

Lienzo azul noche sereno (nunca grita), tipografía amplia, y **un único acento
menta reservado casi por completo para el micrófono** — el héroe de toda la app.
La experiencia central es: ABRIR → HABLAR → INTERPRETAR → CONFIRMAR → RECORDAR.

## Pantallas

- **Login / Registro** — crear cuenta o entrar.
- **Home** — saludo según la hora + secciones `Vencidas`, `Hoy`, `Próximas`,
  cada tarea en una tarjeta con botón de completar. Botón central destacado
  **🎙 Hablar**. Acceso al historial en la barra superior. Enlace secundario
  **+ Crear manualmente**. Estado vacío que invita a hablar.
- **Hoja de voz** (modal) — escuchar → interpretar → confirmar → guardar, con
  pregunta "¿A qué hora?", respuesta hablada para consultas, y manejo de error
  sin conexión.
- **Formulario manual** (crear/editar) — título, detalle, fecha/hora con
  pickers, prioridad y categoría. También permite eliminar.
- **Historial** — actividad reciente (creada, editada, completada, pospuesta,
  seguimientos) en lenguaje natural.

## Estructura

```
lib/
  main.dart                     arranque, permisos, locale es, notificaciones
  models/task.dart              Task, InterpretResult, QueryResult, Category, HistoryEntry
  services/
    api_service.dart            cliente HTTP + JWT (auth, tareas, categorías, historial)
    voice_service.dart          speech_to_text (voz→texto en el dispositivo)
    speech_service.dart         flutter_tts (respuestas habladas)
    notification_service.dart   recordatorios locales + acciones + respuesta por voz
    date_fmt.dart               fechas naturales en español
  screens/
    login_screen.dart
    home_screen.dart            secciones + micrófono + navegación
    voice_sheet.dart            EL flujo de voz, confirmación, búsqueda y seguimientos
    task_form_screen.dart       crear/editar manual
    history_screen.dart         actividad reciente
  widgets/task_card.dart
  theme/app_theme.dart          identidad visual
android/app/src/main/
  AndroidManifest.xml           permisos + widget + acciones de notificación
  kotlin/.../VoxTaskWidgetProvider.kt   widget de pantalla de inicio
  res/layout|drawable|xml/      recursos del widget
```

## Cómo obtener el APK (sin instalar nada)

Este proyecto incluye un flujo de **GitHub Actions** que compila el APK en la
nube. Sigue la guía paso a paso en **`COMO_COMPILAR_APK.md`**: subes el proyecto
a GitHub, la compilación arranca sola, y descargas el `app-release.apk` listo
para instalar en tu celular. Toma unos 5–8 minutos y no requiere instalar Flutter.

## Cómo ejecutar en desarrollo (con Flutter instalado)

1. Levanta el backend primero (ver el otro proyecto):
   ```bash
   uvicorn app.main:app --reload
   ```
2. Instala Flutter (3.3+) y las dependencias:
   ```bash
   flutter pub get
   ```
3. En `lib/services/api_service.dart`, `baseUrl` ya apunta a `10.0.2.2:8000`
   (host desde el emulador Android). Para un dispositivo físico usa la IP de
   tu máquina.
4. Ejecuta:
   ```bash
   flutter run
   ```

## Permisos

Se piden en contexto al arrancar: **micrófono** (captura de voz) y
**notificaciones** (recordatorios). El manifiesto ya incluye alarmas exactas y
arranque tras reinicio para que los recordatorios sean fiables.

## Notas de diseño

- Voz→texto ocurre **en el dispositivo** (rápido y privado); solo la
  interpretación con IA usa la red.
- Notificaciones **locales**, no push: los recordatorios ya guardados funcionan
  sin internet.
- Si la IA no responde (sin conexión), la hoja de voz degrada con elegancia y
  ofrece crear la tarea manualmente.

## Búsqueda por voz

El mismo micrófono sirve para **preguntar**, no solo crear. El backend detecta
si dijiste una tarea o una pregunta. Ejemplos que funcionan:

- "¿Qué tengo hoy?" / "¿Qué tengo para mañana?"
- "¿Qué tareas tengo esta semana?"
- "¿Qué cosas tengo pendientes con Juan?"
- "¿Qué tareas tengo de Formas?"
- "¿Qué tareas vencidas tengo?"

La app muestra la respuesta y **la lee en voz alta** (flutter_tts), luego lista
las tareas encontradas y ofrece "Preguntar otra" para seguir la conversación.

## Seguimientos condicionales

Puedes decir *"recuérdame llamar a Juan mañana y si no lo completo,
recuérdamelo el viernes"*. La tarjeta de confirmación muestra el seguimiento
("Te insisto el viernes… si no la completas"). Al abrir la app, esta evalúa los
seguimientos vencidos: si la tarea sigue pendiente, reprograma la notificación.

## Respuesta por voz desde la notificación

La notificación de recordatorio trae tres acciones: **Completar**, **Posponer**
y **Abrir**. "Posponer" abre un campo de respuesta cuyo teclado incluye el botón
de dictado del sistema, así el usuario puede **decir** "en 1 hora", "mañana" o
"esta tarde" y la app calcula el nuevo horario. Completar y posponer se aplican
directo al backend sin abrir la app.

## Widget de pantalla de inicio

Un widget de Android (`VoxTaskWidgetProvider`) coloca un botón de micrófono en
la pantalla de inicio. Al tocarlo, abre la app directo en el flujo de voz, sin
navegar. Los recursos están en `android/app/src/main/res/`. (En iOS se implementa
después con un App Extension; la lógica Flutter con `home_widget` ya está lista.)

## Estado

MVP completo + búsqueda por voz + seguimientos condicionales + creación/edición
manual + historial + respuesta por voz en notificación + widget Android.

## Pendiente (fases posteriores)

Widget iOS, sincronización multidispositivo, versión web, integración con Google
Calendar / Outlook, y API pública.
