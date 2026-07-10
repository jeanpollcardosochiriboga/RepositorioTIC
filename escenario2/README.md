# Escenario 2 — Simulación de Phishing Educativo (Mu1ticines)

Prototipo de ciberseguridad. Simula un sitio web de cine falso ("Mu1ticines", typosquat de multicines.com.ec) para capturar datos personales y redirigir al usuario a una página de concientización sobre phishing.

## Cómo funciona

```
Usuario → Sitio Mu1ticines (carrusel de películas dinámico)
       → Selector de asiento y horario
       → Formulario de reserva (captura nombre, teléfono, sede + email)
       → Node-RED espera 10 s y envía correo de "confirmación"
       → Usuario hace clic en el enlace del correo
       → Página educativa: "Fuiste víctima de phishing"
```

El indicador de phishing clave: la URL usa `mu1ticines` (con el número `1`) en lugar de `multicines` (con la letra `l`).

## Requisitos previos

- Docker y Docker Compose instalados
- Cuenta Gmail con **App Password** habilitada (no la contraseña normal de Gmail)
  - Activar en: Google Account → Seguridad → Verificación en 2 pasos → Contraseñas de aplicación
- Cuenta gratis en [TMDB](https://www.themoviedb.org/signup) con un **API Read Access Token v4** (cartelera dinámica)
  - Crear en: https://www.themoviedb.org/settings/api → Create → tipo Developer → uso "educational/thesis"
  - Copiar el **Read Access Token** largo (tipo JWT), no la API Key v3 corta

## Setup rápido

```bash
# 1. Clonar el monorepo y entrar en la carpeta del escenario
git clone https://github.com/jeanpollcardosochiriboga/RepositorioTIC.git
cd RepositorioTIC/escenario2

# 2. Crear el archivo de configuración y completarlo con los valores reales
cp .env.example .env

# 3. Arrancar
docker compose up -d

# Ver los logs en tiempo real
docker compose logs -f
```

El servicio queda disponible en `http://localhost:1882`.

## Variables de entorno (.env)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SMTP_USER` | Cuenta Gmail usada como remitente | `tu_cuenta@gmail.com` |
| `SMTP_PASS` | App Password de Gmail (16 caracteres) | `abcd efgh ijkl mnop` |
| `BASE_URL` | URL pública del servidor | `http://192.168.1.10:1882` |
| `SENDER_NAME` | Nombre visible en el correo | `Mu1ticines Sorteos` |
| `SMTP_SERVER` | Servidor SMTP (opcional) | `smtp.gmail.com` |
| `SMTP_PORT` | Puerto SMTP (opcional) | `465` |
| `TMDB_TOKEN` | Read Access Token v4 de TMDB | `eyJhbGciOiJIUzI1NiJ9...` |
| `TMDB_LANGUAGE` | Idioma de los textos | `es-MX` |
| `TMDB_REGION` | Región para `now_playing` | `EC` |

> **Nota de seguridad:** Nunca subas el archivo `.env` al repositorio. Está excluido en `.gitignore`.

## Arquitectura

```
docker-compose.yml
├── Dockerfile          → Node.js 18 Alpine + Node-RED
├── flows.json          → Lógica backend (Node-RED) — no editar a mano
├── settings.js         → Configuración de Node-RED
├── www/                → Frontend estático servido por Node-RED
│   ├── index.html      → Carrusel de películas + selector de asientos + formulario
│   ├── movies.json     → Cartelera (autogenerada por refresh_movies.py — no editar a mano)
│   ├── consent.html    → Formulario de consentimiento / captura de datos
│   └── educativo.html  → Página de concientización sobre phishing
└── scripts/
    └── send_email.py   → Envío de correo vía Gmail SMTP
```

## Cartelera dinámica (TMDB)

La cartelera se actualiza **automáticamente** desde la API de TMDB. Una vez que `TMDB_TOKEN` está en el `.env`, el operador no toca nada: solo arranca el contenedor.

### Cuándo se actualiza

| Evento | Acción |
|---|---|
| Arranque del contenedor | 15 s después de boot, refresh automático |
| Cron interno | Todos los días a las 06:00 |
| Manual (opcional) | `docker exec jp-esc2-nodered python3 /data/scripts/refresh_movies.py` |

### Qué cartelera se trae

Orden de prioridad (cae al siguiente si devuelve menos de 4 películas):

1. `/movie/now_playing?region=EC` — estrenos en cines del Ecuador
2. `/movie/now_playing` — estrenos globales (suele ser la fuente real, ~20 películas)
3. `/movie/popular` — populares del mes (último recurso)

Los posters se sirven desde el CDN de TMDB (`image.tmdb.org`); no se descargan localmente. La frecuencia de cambio en TMDB es: **se renueva varias veces por semana**. En 6 meses la cartelera será 100 % distinta a la actual sin que tengas que hacer nada.

### Comportamiento sin internet

Si TMDB no responde el script falla *sin tocar* `www/movies.json`. El frontend sigue sirviendo la última cartelera buena conocida. El repo trae un `movies.json` ya poblado para el primer arranque sin internet. Lo único que se rompe sin internet son los **posters** (vienen del CDN de TMDB) y el **envío de correo SMTP**.

### Runbook del operador (6 meses después, sin saber nada del proyecto)

Caso normal — solo encender:

```bash
ssh raspberry1@192.168.1.10
cd ~/RepositorioTIC/escenario2
docker compose up -d
docker compose logs -f          # esperar el mensaje "OK: movies.json refrescado"
```

Si en los logs aparece `OK: movies.json refrescado (N películas, fuente=estreno)` → todo bien, cartelera fresca.

Si aparece `ERROR: TMDB inalcanzable` → no hay internet en ese momento; el frontend igual funciona con la cartelera anterior. Conecta internet y reinicia con `docker compose restart` para regenerar.

Si aparece `HTTP Error 401` o `Unauthorized` → el token de TMDB fue revocado o la cuenta fue suspendida. Ver siguiente sección.

### Riesgos del token TMDB y cómo regenerarlo

El token v4 de lectura **no expira por tiempo**, pero puede dejar de funcionar si:

- La cuenta TMDB asociada es eliminada o suspendida por inactividad prolongada (TMDB no documenta el plazo, pero cuentas activas suelen mantenerse indefinidamente).
- El usuario revoca manualmente el token desde [Settings → API](https://www.themoviedb.org/settings/api).
- TMDB cambia su política de API (poco probable; la v4 es estable desde 2018).

**Para regenerar el token** (si dejara de funcionar):

1. Entrar a https://www.themoviedb.org/settings/api con la cuenta del autor.
2. Si la cuenta sigue activa: copiar el "API Read Access Token" actual.
3. Si la cuenta fue eliminada: crear nueva cuenta TMDB, generar token nuevo (~5 min, ver sección "Requisitos previos").
4. Editar `.env` del Pi: `TMDB_TOKEN=<nuevo token>`
5. Reiniciar: `docker compose restart`

**Recomendación**: una vez al año entrar a la cuenta TMDB para mantener actividad y evitar suspensión por inactividad.

### Logs y debug

```bash
docker compose logs -f                                          # logs en tiempo real
docker exec jp-esc2-nodered cat /data/www/movies.json | head    # ver cartelera actual
```

También se puede abrir el panel de debug de Node-RED en `http://<IP>:1882/admin` y ver los mensajes del nodo "TMDB refresh log".

## Cómo modificar el flujo (Node-RED)

Con el contenedor en marcha (`docker compose up -d`), los cambios se hacen en el editor visual
(`http://localhost:1882/admin`) y se exportan con **Menú (≡) → Export → Download**, que reemplaza el
`flows.json` del proyecto. El archivo es sensible al orden, así que no conviene editarlo a mano.

## Código QR del dashboard

El QR del dashboard se genera automáticamente usando `BASE_URL` del archivo `.env`. No requiere ningún paso adicional — con configurar `BASE_URL` correctamente el QR apunta a la instalación correcta.

## Dependencia de Internet

El envío de correo usa SMTP sobre TLS (puerto 465, `smtp.gmail.com`). Sin conexión a Internet el envío
falla en silencio: el usuario no ve ningún error en el sitio, pero el correo nunca llega. La cartelera y
los pósters también dependen de Internet; sin él, el sitio sigue sirviendo la última cartelera conocida.

Para evitarlo conviene asegurar la salida a Internet del gateway antes de la demostración (ver
[`../infraestructura/README.md`](../infraestructura/README.md)) y comprobar `ping 8.8.8.8` desde un
dispositivo de la red. Como respaldo, tener a la mano una captura del correo de confirmación de una
presentación anterior para mostrarla en el momento del flujo.

## Detener el servicio

```bash
docker-compose down
```
