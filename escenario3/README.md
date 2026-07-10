# Escenario 3 — Simulador de Ataque DoS "Colapso Controlado"

Prototipo de ciberseguridad

## Descripción

Demostración interactiva de un ataque de Denegación de Servicio (DoS) en vivo. El público de la feria usa sus celulares para lanzar el ataque desde una página web, sin instalar nada. El objetivo es un servidor vulnerable diseñado intencionalmente para colapsar. Todo ocurre dentro de una red Docker aislada, sin impacto en la red física de la feria.

### Fases de la demostración

1. **Ataque**: Los asistentes escanean el QR, aceptan el consentimiento y pulsan el botón rojo. El servidor se cae (Timeout visible en el dashboard).
2. **Recuperación**: El presentador detiene el ataque. El servidor vuelve a verde.
3. **Protección**: El presentador reactiva el ataque y activa el mecanismo de protección (rate limiting vía nginx). El servidor se recupera aunque el ataque continúa.

## Arquitectura

```
Red Docker aislada: esc3-net
│
├── esc3-nodered   [:1883] ── Orquestador + Dashboard + Página móvil
├── esc3-target    [:5000] ── App vulnerable (Flask single-thread)
├── esc3-attacker  [:5001] ── Arma HTTP (Python asyncio + FastAPI)
└── esc3-proxy     [:8080] ── Nginx rate-limiting (mecanismo de protección)
```

**Flujo del ataque (sin protección):**
`esc3-attacker → esc3-target:5000/reservar` → timeout/caída

**Flujo con protección activa:**
`esc3-attacker → esc3-proxy:8080` → rate limit ≤5 req/s → `esc3-target` se recupera

## Páginas del Dashboard (proyección)

| Tab | Contenido |
|-----|-----------|
| **Código QR** | QR grande para que el público escanee y llegue a la página móvil |
| **Ataque en Vivo** | Animación SVG + métricas RPS / RT + botones de control |
| **Estadísticas** | RPS pico, participantes totales |

## Página Móvil del Público

Acceso via QR o directamente a `http://<IP>:1883/`

1. `consent.html` — Consentimiento informado (primera visita)
2. `alias.html` — El participante elige un apodo (aparece en el dashboard)
3. `index.html` — Botón rojo de ataque + estado del servidor en tiempo real

### Instrucciones para el público antes de la demo

> **"Para participar necesitan hacer dos cosas: primero conectarse a la red WiFi llamada _CASA ABIERTA TI_ (sin contraseña), y luego escanear el código QR que aparece en pantalla. Los lleva directo a su arma de ataque."**

- Sin estar en esa red, el QR no funciona — el celular no alcanza el servidor local.
- El QR se muestra en el tab **Código QR** del dashboard (proyección).
- Cada participante elige un apodo; aparece en la lista "Atacantes en vivo" del dashboard.

## Inicio Rápido

```bash
cd tesis_escenario3
cp .env.example .env        # Ajustar DASH_IP y WORKERS si necesario
docker-compose up -d
```

Verificar que los 4 contenedores están activos:

```bash
docker-compose ps
```

Acceder al dashboard:

```
http://localhost:1883/ui       # Dashboard (proyección)
http://localhost:1883/admin    # Editor Node-RED
http://localhost:1883/         # Página móvil del público
```

## Configuración (`.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DASH_PORT` | Puerto externo del dashboard | `1883` |
| `DASH_IP` | IP del host (para QR, si auto-detect falla) | `192.168.1.100` |
| `WORKERS` | Workers concurrentes del attacker | `50` |
| `TARGET_URL` | URL inicial del objetivo | `http://esc3-target:5000/reservar` |

## API de Control (Node-RED → Attacker)

| Endpoint | Método | Acción |
|----------|--------|--------|
| `/api/attack/start` | POST | Lanzar el ataque |
| `/api/attack/stop` | POST | Detener el ataque |
| `/api/protect` | POST | Activar rate limiting (cambiar target a proxy) |
| `/api/attack/press` | POST | Registrar press del público (celulares) |
| `/api/attack/status` | GET | Obtener contador de participantes |

## Vulnerabilidad del Servidor Target

El servidor `esc3-target` usa Flask con `threaded=False` (un hilo único). La ruta `/reservar` hace `time.sleep(2)`, bloqueando completamente el proceso. Bajo flood de 50+ workers concurrentes, la cola de conexiones TCP se llena y el servidor deja de responder (Timeout).

## Mecanismo de Protección

El proxy nginx en `esc3-proxy:8080` aplica:
```
rate=5r/s, burst=10 nodelay
```
Requests que excedan el límite reciben **HTTP 429**. El target pasa de recibir cientos de req/s a solo 5, lo que permite que se recupere.

---

## Pitch de Presentación (Escenario 3)

> **Nota:** Falta redactar pitches equivalentes para Escenario 1 (monitoreo de red y DNS) y Escenario 2 (phishing simulado). Seguir la misma estructura: gancho cotidiano → concepto en 30 s → demo → defensa → cierre con dato real → pregunta al público.

### Gancho de apertura (elige según el momento)

> *"¿Alguna vez entraron al portal del SRI o del IESS el 31 de marzo, el último día para declarar impuestos, y el sistema simplemente no cargaba? Eso que vivieron tiene un nombre."*

> *"En el Mundial 2022, cuando Ecuador jugó, los portales de streaming colapsaron en todo el país. En las elecciones de 2023, páginas del CNE dejaron de responder durante horas. ¿Qué tienen en común esos eventos?"*

### El concepto en 30 segundos

> Imaginen que esta sala es un banco. La puerta tiene capacidad para que entren **5 personas a la vez**. Si yo mando a **200 personas** a intentar entrar al mismo tiempo, la puerta colapsa — no porque esté rota, sino porque fue diseñada para carga normal. Un ataque de Denegación de Servicio funciona exactamente así: no hackea el sistema, **lo ahoga con tráfico legítimo hasta que deja de responder para todos**.

### La demo

> El servidor que ven en pantalla simula el sistema de gestión de transporte de CONAFIPS — una entidad financiera pública real. Cada uno de ustedes tiene en su teléfono un botón de ataque. Cuando lancemos el ataque coordinado, van a ver en tiempo real cómo el servidor pasa de *verde a amarillo a rojo*. Y cuando llegue a caído — van a ver exactamente por qué esto es un problema real.

### Después de la demo (protección)

> Ahora activo el mecanismo de defensa: un proxy con **rate limiting**. Le dice al servidor: *"acepta máximo 5 peticiones por segundo, el resto se descarta"*. En segundos el sistema se recupera. Esta es la diferencia entre tener o no tener una capa de protección frente a un ataque volumétrico.

### Cierre

> En 2016, una botnet llamada Mirai usó *cámaras de seguridad y routers domésticos* mal configurados para tirar abajo Twitter, Netflix y Spotify durante horas. Los dispositivos de las víctimas fueron los atacantes sin que sus dueños lo supieran. Esa es la razón por la que la ciberseguridad no es solo un problema de grandes empresas — **cada dispositivo conectado que no está protegido es una puerta abierta**.

### Pregunta de cierre al público

> *"¿Cuántos de ustedes tienen cámaras IP, routers o dispositivos domésticos en casa sin cambiar la contraseña de fábrica?"* — [pausa] — *"Esos dispositivos podrían estar participando en un ataque como este ahora mismo sin que lo sepan."*

---

## Despliegue en Raspberry Pi 3B+

> Ejecutar estos pasos solo al migrar a la Pi. Durante el desarrollo local, no son necesarios.

1. Copiar el proyecto a la Pi: `rsync -av tesis_escenario3/ pi@<IP>:~/tesis_escenario3/`
2. Bajar los otros escenarios: `docker-compose -f ../Escritorio/tesis_escenario1/docker-compose.yml down` y `docker-compose -f ../tesis_escenario2/docker-compose.yml down`
3. En `.env` de la Pi: reducir `WORKERS=30`
4. Agregar límites de recursos en `docker-compose.yml`:

```yaml
services:
  esc3-nodered:
    cpus: 0.8
    mem_limit: 384m
  esc3-target:
    cpus: 0.3
    mem_limit: 64m
  esc3-attacker:
    cpus: 1.5
    mem_limit: 128m
  esc3-proxy:
    cpus: 0.2
    mem_limit: 32m
```

5. Agregar `restart: unless-stopped` a todos los servicios
6. Verificar que la Pi detecta la IP correcta: `hostname -I | awk '{print $1}'`
7. Actualizar `/etc/hosts` en la máquina del presentador si se usa `esc3.jp.local`

## Workflow Node-RED

Editar flows desde el editor en `/admin`, luego exportar:
**Menú → Export → Download** → sobreescribir `flows.json` → commit.

No editar `flows.json` a mano: el JSON es machine-generated y order-sensitive.

## Git

```bash
# Inicializar repo (primera vez)
git init
git remote add origin https://github.com/jeanpollcardosochiriboga/<REPO>.git
git branch -m main Branch_Escenario3_DoS_Funcional
```

Push requiere GitHub Personal Access Token (no hay SSH keys configuradas).

---

## Resumen técnico para el tutor

**4 contenedores Docker en red interna aislada (`esc3-net`). Sin acceso a internet entre ellos.**

| Contenedor | Tecnología | Rol |
|---|---|---|
| `esc3-nodered` | Node-RED + node-red-dashboard | Orquestador central: sirve el dashboard de proyección, la página móvil del público, y coordina todo el flujo de la demo via HTTP. |
| `esc3-target` | Flask (Python, hilo único, `sleep(2)`) | Víctima intencional. Un servidor deliberadamente vulnerable: procesa una sola petición a la vez; bajo carga colapsa. |
| `esc3-attacker` | Python asyncio + FastAPI | Motor del ataque. Lanza N workers concurrentes de HTTP flood contra el target. Controlable via API REST (`/start`, `/stop`, `/target`). |
| `esc3-proxy` | Nginx | Mecanismo de defensa. Actúa como reverse proxy con rate limiting (5 req/s). Al activarlo, el target se recupera aunque el flood continúe. |

**Flujo completo:**

```
Celulares del público
  └─ POST /api/attack/press ──► Node-RED (registra participantes, actualiza dashboard)

Presentador pulsa LANZAR
  └─ Node-RED ──► POST esc3-attacker:5001/start
       └─ 50 workers asyncio ──► POST esc3-target:5000/reservar  (flood)
            └─ Target colapsa → health check devuelve timeout → dashboard rojo

Presentador pulsa PROTEGER
  └─ Node-RED ──► POST esc3-attacker:5001/target  (cambia URL a proxy)
       └─ 50 workers ──► esc3-proxy:8080  (nginx filtra a 5 req/s)
            └─ Target recibe carga manejable → se recupera → dashboard verde
```

**Por qué colapsa el target:** Flask con `threaded=False` + `time.sleep(2)` por petición. Con 50 workers concurrentes, la cola TCP se llena en segundos. Es una vulnerabilidad de diseño intencional para la demo, no un exploit.
