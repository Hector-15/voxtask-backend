# Cómo obtener el APK con GitHub Actions

Esta guía te lleva de cero al APK instalado en tu celular, **sin instalar nada**
en tu computadora. Todo se compila en los servidores de GitHub.

---

## Paso 1 — Crear un repositorio en GitHub

1. Entra a https://github.com y crea una cuenta si no tienes.
2. Haz clic en **New repository**, ponle nombre (p. ej. `voxtask`), déjalo
   **Private** o **Public** como prefieras, y créalo.

## Paso 2 — Subir el proyecto

Tienes dos formas:

**Forma fácil (sin comandos, desde el navegador):**
1. En tu repo nuevo, haz clic en **uploading an existing file**.
2. Arrastra **todo el contenido** de la carpeta `voxtask-app` (no la carpeta en
   sí, sino lo que hay dentro: `lib/`, `android/`, `pubspec.yaml`, la carpeta
   oculta `.github/`, etc.).
   - ⚠️ Importante: la carpeta `.github/` empieza con punto. Si tu explorador de
     archivos no muestra archivos ocultos, actívalos, o usa la forma con Git.
3. Escribe un mensaje ("primer commit") y confirma.

**Forma con Git (si lo tienes):**
```bash
cd voxtask-app
git init
git add .
git commit -m "Primer commit de VoxTask"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/voxtask.git
git push -u origin main
```

## Paso 3 — Dejar que compile

- Si subiste a la rama `main`, **la compilación arranca sola**.
- Si no, ve a la pestaña **Actions** del repo, elige **Build APK** en la
  izquierda y pulsa **Run workflow**.

La compilación tarda unos **5–8 minutos**. Verás un círculo amarillo (en curso)
que pasa a verde (listo) o rojo (error).

## Paso 4 — Descargar el APK

1. Entra a la pestaña **Actions** → haz clic en la ejecución que terminó en
   verde.
2. Baja hasta la sección **Artifacts**.
3. Descarga **voxtask-apk**. Es un `.zip`; ábrelo y dentro está
   `app-release.apk`.

## Paso 5 — Instalar en el celular

1. Pasa el `app-release.apk` a tu teléfono (por cable, Drive, Telegram, etc.).
2. Ábrelo desde el celular. Android te pedirá permiso para
   **instalar apps de orígenes desconocidos** — actívalo para tu explorador de
   archivos o navegador.
3. Instala y abre VoxTask.

---

## Antes de que funcione del todo: el backend

La app necesita hablar con el backend (la parte de IA). Dos opciones:

- **Para probar rápido:** corre el backend en tu computadora
  (`uvicorn app.main:app --host 0.0.0.0 --reload`) y en
  `lib/services/api_service.dart` cambia `baseUrl` por la IP de tu PC en la red
  local (p. ej. `http://192.168.1.50:8000`). Celular y PC en el mismo WiFi.
- **Para usarlo en cualquier lugar:** despliega el backend en un servicio como
  Render, Railway o Fly.io (tienen planes gratuitos) y pon esa URL en `baseUrl`.

> Si cambias `baseUrl`, vuelve a hacer push: GitHub Actions recompila el APK con
> la nueva dirección automáticamente.

---

## Si la compilación falla (rojo)

Abre la ejecución roja en **Actions**, despliega el paso que falló y lee el
mensaje. Lo más común:
- **Versión de un paquete incompatible** → en `pubspec.yaml`, relaja la versión
  del paquete señalado (p. ej. cambia `^17.0.0` por una versión que exista) y
  vuelve a hacer push.
- El workflow ya está configurado para que `flutter analyze` no bloquee el build,
  así que los avisos de estilo no impiden generar el APK.
