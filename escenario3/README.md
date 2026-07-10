# Escenario 3. Denegación de servicio controlada («Colapso Controlado»)

Prototipo de ciberseguridad.

Demostración interactiva de un ataque de denegación de servicio (DoS) en vivo. El público usa su
propio celular para lanzar el ataque desde una página web, sin instalar nada. El objetivo es un
servidor vulnerado a propósito para que colapse. Todo ocurre dentro de una red Docker aislada, sin
efecto sobre la red física de la sede.

## Fases de la demostración

1. **Ataque.** Los asistentes escanean el QR, aceptan el consentimiento y pulsan el botón de ataque. El
   servidor deja de responder y el panel lo marca en rojo.
2. **Recuperación.** El expositor detiene el ataque y el servidor vuelve a verde.
3. **Protección.** El expositor reactiva el ataque y enciende el mecanismo de protección (limitación de
   tasa con nginx). El servidor se recupera aunque el ataque continúe.

## Arquitectura

Cuatro contenedores en una red Docker aislada (`esc3-net`), sin salida a Internet entre ellos:

| Contenedor | Tecnología | Rol |
|---|---|---|
| `esc3-nodered` (`:1883`) | Node-RED + node-red-dashboard | Orquesta la demo, sirve el panel de proyección y la página móvil del público |
| `esc3-target` (`:5000`) | Flask de un solo hilo con una espera bloqueante | Víctima intencional: atiende una petición a la vez y colapsa bajo carga |
| `esc3-attacker` | Python asyncio + FastAPI | Motor del ataque: lanza peticiones concurrentes contra el objetivo |
| `esc3-proxy` | nginx | Defensa: proxy inverso con limitación de tasa (5 peticiones por segundo) |

```
Sin protección:   esc3-attacker → esc3-target:5000/reservar        → el objetivo colapsa
Con protección:   esc3-attacker → esc3-proxy → 5 req/s → esc3-target → el objetivo se recupera
```

**Por qué colapsa el objetivo:** el servidor Flask corre con un solo hilo y cada petición a `/reservar`
espera unos segundos de forma bloqueante. Con decenas de peticiones concurrentes la cola de conexiones
se llena y el servidor deja de responder. Es una vulnerabilidad de diseño para la demostración, no un
exploit.

## Despliegue

```bash
git clone https://github.com/jeanpollcardosochiriboga/RepositorioTIC.git
cd RepositorioTIC/escenario3
cp .env.example .env          # ajustar WORKERS y DASH_IP si hace falta
docker compose up -d --build
docker compose ps             # los cuatro contenedores deben estar activos
```

Direcciones:

```
http://localhost:1883/ui       # panel de proyección
http://localhost:1883/admin    # editor de Node-RED
http://localhost:1883/         # página móvil del público
```

En la Raspberry Pi se recomienda `WORKERS=30`. La red aislada y la salida a Internet las provee la
infraestructura común; ver [`../infraestructura/README.md`](../infraestructura/README.md).

## Configuración (`.env`)

| Variable | Descripción | Por defecto |
|---|---|---|
| `DASH_PORT` | Puerto externo del panel | `1883` |
| `DASH_IP` | IP del servidor, respaldo del QR si la autodetección falla | `192.168.1.10` |
| `WORKERS` | Peticiones concurrentes del atacante (`30` en la Pi) | `50` |
| `TARGET_URL` | URL inicial del objetivo | `http://esc3-target:5000/reservar` |

## Páginas del panel (proyección)

| Pestaña | Contenido |
|---|---|
| **Código QR** | Código grande para que el público lo escanee y llegue a la página móvil |
| **Ataque en Vivo** | Animación del ataque, peticiones por segundo, estado del servidor y botones de control |
| **Encuesta** | Recoge la encuesta final del público |

## Página móvil del público

Se accede por el código QR o directamente en `http://<IP>:1883/`:

1. `consent.html`, consentimiento informado (primera visita).
2. `alias.html`, el participante elige un apodo, que aparece en el panel.
3. `index.html`, botón de ataque y estado del servidor en tiempo real.

Para participar, el celular debe estar en la misma red WiFi que difunde el prototipo en esa sede; sin
eso, el QR no alcanza al servidor local. El nombre de la red se define al montar la demostración, no es
fijo.

## API de control (Node-RED)

| Extremo | Método | Acción |
|---|---|---|
| `/api/attack/press` | POST | Registra el toque de un celular del público |
| `/api/attack/status` | GET | Devuelve el conteo de participantes |
| `/api/attack/start` | POST | Lanza el ataque |
| `/api/attack/stop` | POST | Detiene el ataque |
| `/api/protect` | POST | Activa la limitación de tasa (redirige el tráfico al proxy) |
| `/api/survey` | POST | Recibe la encuesta del público y la anexa a un CSV |
| `/api/export_state` | GET | Entrega una instantánea del estado para la recolección de métricas |

Node-RED traduce estas acciones a la API interna del atacante (`/start`, `/stop`, `/target`).

## Mecanismo de protección

El proxy `esc3-proxy` limita el tráfico a 5 peticiones por segundo; las que exceden reciben **HTTP 429**.
El objetivo pasa de cientos de peticiones por segundo a solo cinco, con lo que se recupera aunque el
ataque siga.

## Modificar el flujo (Node-RED)

Los cambios se hacen en el editor visual (`/admin`) y se exportan con **Menú → Export → Download**, que
reemplaza `flows.json`. El archivo es generado por la herramienta y es sensible al orden, así que no
conviene editarlo a mano.

## Detener

```bash
docker compose down
```
