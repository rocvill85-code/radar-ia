# Radar IA · 9dieciséis — Puesta en marcha (2 minutos)

Esta carpeta ya es un repositorio Git listo para subir. Sigue estos pasos **en una terminal interactiva** (donde puedas hacer login en GitHub). Copia y pega tal cual.

---

## Paso 1 · Crear el repositorio en GitHub
1. Entra en https://github.com/new
2. **Repository name:** `radar-ia`
3. Déjalo **Private** (privado). NO marques "Add a README".
4. Pulsa **Create repository**.

## Paso 2 · Conectar y subir (pega esto en la terminal, dentro de la carpeta `radar-ia`)
Sustituye `TU-USUARIO` por tu usuario de GitHub:

```bash
git remote add origin https://github.com/TU-USUARIO/radar-ia.git
git branch -M main
git push -u origin main
```

La primera vez te pedirá iniciar sesión en GitHub en el navegador. Acéptalo.

## Paso 3 · Activar la web (GitHub Pages)
1. En tu repo: **Settings → Pages**.
2. En **Source**, elige **Deploy from a branch**.
3. Branch: **main**, carpeta **/ (root)**. **Save**.
4. En ~1 minuto tendrás tu URL pública:
   `https://TU-USUARIO.github.io/radar-ia/`
   Esa es la URL que compartes con las 2 personas y que se instala en el móvil (icono incluido).

## Paso 4 · Dime que está listo
Vuelve aquí y escríbeme: **"repo listo, usuario: TU-USUARIO"**.
Con eso creo el **agente automático de los lunes**: cada lunes buscará las noticias de la semana, actualizará la revista y la publicará sola en tu URL. No tendrás que tocar nada más.

---

## ¿Qué hay en esta carpeta?
- `index.html` — la revista (versión instalable, con icono de app).
- `icon-180 / 512 / 1024.png` — iconos de la app.
- `manifest.webmanifest` — hace que se instale como app en el móvil.
- `artifact-source.html` — copia de la versión Artifact (por si se republica en claude.ai).
- `PONER-EN-MARCHA.md` — esta guía.

## Actualización semanal (cómo funcionará)
Una vez creado el agente, cada lunes por la mañana (hora de Madrid):
1. Busca noticias reales de IA en audiovisual, marketing/estrategia y project management.
2. Redacta en español y marca con ◎ las relevantes para 9dieciséis.
3. Actualiza `index.html` y sube los cambios → tu web se actualiza sola.

Mientras tanto, siempre puedes pedirme a mano: *"actualiza el Radar IA"*.
