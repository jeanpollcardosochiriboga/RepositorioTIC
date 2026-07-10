# metricas — Recolección de métricas (§4 del marco teórico)

Recolecta las métricas del **§4** del marco teórico (satisfacción, desempeño
funcional, consumo de recursos, tiempo de montaje y despliegue) para los tres
escenarios, **uno a la vez**.

## Arquitectura

**Toda la recolección corre EN EL PI.** La laptop solo dispara la sesión por SSH y descarga
los CSV para graficar — nunca recolecta (pedido del tutor). Un solo reloj (el de la Pi).

```
┌──────────────── Pi 3B+ (192.168.1.10) — RECOLECTA TODO ───────────────┐
│  contenedores del escenario (escN-nodered, …)                          │
│  collect_resources.py   ──► resources.csv      (psutil + docker SDK)   │
│  collectors/collect_router.py ──► router*.csv  (ssh OpenWrt 192.168.1.1)│
│  collectors/docker_events_collector.py ──► docker_events.csv           │
│  collectors/target_health_probe.py ──► target_health.csv (solo Esc3)   │
│  collectors/measure_deploy.py ──► deploy.csv                           │
│  middleware Node-RED    ──► backend_latency.csv                        │
│  /api/export_state      ──► tablas de dominio                          │
│  session.sh ── coordina (con guard: aborta si no corre en el Pi)       │
└────────────────────────────┬───────────────────────────────────────────┘
                             │ la laptop dispara por SSH y, al cerrar,
                             │ descarga la carpeta de sesión (scp)
                             ▼
                  ┌───────── Laptop (solo visualiza) ──────────┐
                  │  gateway/session.ps1  (SSH + scp, no mide)  │
                  │  análisis y gráficas (fuera de este repo)   │
                  └─────────────────────────────────────────────┘
```

## Outputs por sesión

Una carpeta `sessions/<fecha>_<escenario>/` (ej. `2026-05-22_esc1/`):

| Archivo | Origen | Cadencia |
|---|---|---|
| `resources.csv` | `pi/collect_resources.py` (psutil + docker SDK) | 1/s |
| `router.csv` | `collectors/collect_router.py` (tráfico agregado) | 1/5s |
| `router_devices.csv` | `collectors/collect_router.py` (MAC/IP/hostname por equipo) | 1/5s |
| `router_resources.csv` | `collectors/collect_router.py` (CPU/RAM del router) | 1/5s |
| `backend_latency.csv` | middleware Node-RED (`metrics_middleware.js`) | 1/petición |
| `deploy.csv` | `collectors/measure_deploy.py` | 1/despliegue |
| `target_health.csv` | `collectors/target_health_probe.py` (solo Esc3) | 1/s |
| `docker_events.csv` | `collectors/docker_events_collector.py` | por evento |
| `loadtest.csv` | `collectors/loadgen.py` (solo lab) | 1/escalón |
| `survey.csv` | form HTML → `/api/survey` | 1/encuestado |
| `events.csv` | `session.sh log` (anotaciones del operador) | discreto |
| tablas de dominio | `fetch_export_state.py` ← `/api/export_state` (al cerrar) | 1 vez |

## Uso por sesión

Primero **dejar desplegado solo el escenario a medir** (bajar los otros dos en el Pi).

**Desde la laptop (recomendado)** — el wrapper dispara `session.sh` EN EL PI por SSH y, al
cerrar, descarga la carpeta de sesión. La laptop nunca recolecta:

```powershell
# PowerShell en la laptop (gateway Windows)
cd metricas\gateway
.\session.ps1 start esc1     # arranca los medidores EN EL PI (escenario aún abajo)
.\session.ps1 deploy         # mide tiempo de despliegue en frío -> deploy.csv
.\session.ps1 log montaje_fisico_s 95   # montaje físico (cronómetro del operador)
# ... corre la demo ...
.\session.ps1 status         # colectores activos y filas por CSV (en el Pi)
.\session.ps1 end            # cierra en el Pi y descarga la carpeta a sessions\
```

**Directo en el Pi** (equivalente; `PI_PASS`/`ROUTER_PASS` en el `.env` de esta carpeta):

```bash
# por SSH dentro del Pi, en la carpeta metricas del repo clonado
./session.sh start esc1      # session.sh aborta si NO corre en el Pi (guard de host)
./session.sh deploy ; ./session.sh status ; ./session.sh end
```

Pruebas de carga sintética (**solo en laboratorio**, nunca en demo pública; corre en el Pi):

```bash
python3 collectors/loadgen.py --config config/esc1.yaml --output-dir sessions/<id>/
```

## Análisis

Las gráficas y tablas del capítulo de Resultados se producen fuera de este repositorio, a partir de los
CSV de cada sesión. Aquí vive la parte de recolección; el análisis se hace por separado con esos archivos.

## Alcance de `session.sh`

`session.sh` mide un escenario a fondo, incluidas las tablas de dominio (auditoría del Esc1, correos del
Esc2, atacantes del Esc3). Es el flujo que produce los datos analizables.

## Filosofía

- **Mediciones reales, no simuladas**: psutil lee `/proc`; httpx hace HTTP real;
  Node-RED mide en el handler verdadero; el router responde por SSH.
- **Mínimo riesgo de error**: bibliotecas estándar (psutil, httpx, asyncio, pandas);
  CSVs append-only; sin DB; el agente del Pi es un proceso suelto bajo `nohup`.
- **Un solo reloj**: como todos los colectores corren en la Pi, los CSV comparten el reloj de
  la Pi y se unen por timestamp sin sincronizar nada. (`session.sh` conserva un self-check de
  reloj por seguridad.)
- **La laptop solo visualiza**: dispara la sesión por SSH y descarga los CSV; `session.sh` lleva
  un guard que aborta si se ejecuta fuera del Pi.

## Estructura

```
metricas/
├── README.md                  # esta guía
├── session.sh                 # coordina la recolección EN EL PI (start/deploy/log/status/end)
├── requirements.txt
├── gateway/
│   └── session.ps1            # disparador desde la laptop: SSH + descarga (no mide)
├── pi/
│   ├── collect_resources.py   # medidor de recursos, corre en el Pi
│   └── install.sh             # instala el agente + entorno en el Pi
├── collectors/                # medidores que corren EN EL PI (los lanza session.sh)
│   ├── collect_router.py      # tráfico, dispositivos y recursos del router (SSH al OpenWrt)
│   ├── measure_deploy.py      # tiempo de despliegue (compose up -> HTTP 200)
│   ├── target_health_probe.py # disponibilidad del objetivo (Esc3)
│   ├── docker_events_collector.py
│   ├── fetch_export_state.py  # tablas de dominio
│   ├── loadgen.py             # rampa de carga sintética (solo laboratorio)
│   └── presentation_watcher.py
├── survey/
│   ├── survey_template.json   # encuesta (editable sin tocar código)
│   ├── form.html
│   └── INSTALL.md
├── templates/
│   └── eisvogel.latex         # plantilla de informe
├── config/{esc1,esc2,esc3}.yaml
└── sessions/                  # salidas por sesión (no versionadas)
```

El medidor de latencia del backend (`metrics_middleware.js`) vive dentro de cada escenario, no aquí.
