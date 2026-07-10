# Recolección de métricas

Recolecta las cuatro métricas del marco teórico, que son la satisfacción de la audiencia, el desempeño
funcional, el consumo de recursos y los tiempos de montaje y despliegue, para los tres escenarios, uno a
la vez. Toda la recolección corre en el Pi, sobre un mismo reloj, para que los datos de cada capa se
crucen en la misma línea de tiempo. La laptop no mide, solo descarga los archivos al terminar.

## Cómo se usa desde la consola del operador

La medición se maneja con botones, sin escribir comandos, desde la consola del operador
(ver [`../infraestructura/consola`](../infraestructura/consola)).

1. Se levanta el escenario a mostrar con su botón y la consola apaga los otros dos.
2. Se pulsa **INICIAR MÉTRICAS** y la consola detecta el escenario activo y arranca los medidores en el Pi.
3. Se corre la demostración.
4. Se pulsa **TERMINAR MÉTRICAS** y la consola cierra los medidores, reúne los archivos de la sesión en el
   Pi y exporta las tablas del escenario.

Los archivos quedan en el Pi, en `sessions/<fecha>_<escenario>/` (por ejemplo `2026-06-24_esc1/`), y se
descargan a la laptop para analizarlos.

El operador mide con cronómetro los tiempos de montaje físico y de despliegue, y los anota junto a los
datos de la sesión. El montaje físico es el tiempo que toma conectar los cables y la alimentación hasta
dejar el equipo listo para encender. El despliegue es el tiempo desde que se enciende hasta que el primer
escenario responde a la primera petición.

## Qué se recolecta

Cada sesión produce una carpeta con estos archivos.

| Archivo | Qué guarda | Origen | Cadencia |
|---|---|---|---|
| `resources.csv` | CPU, memoria y red del servidor y de cada contenedor | `pi/collect_resources.py` | 1/s |
| `router.csv` | tráfico del router | `collectors/collect_router.py` | 1/5 s |
| `router_devices.csv` | equipos conectados (concurrencia real) | `collectors/collect_router.py` | 1/5 s |
| `router_resources.csv` | CPU y memoria del router | `collectors/collect_router.py` | 1/5 s |
| `backend_latency.csv` | latencia del servidor por petición | `metrics_middleware.js` (en cada escenario) | 1/petición |
| `target_health.csv` | disponibilidad del servidor víctima (solo Esc3) | `collectors/target_health_probe.py` | 1/s |
| `docker_events.csv` | reinicios o caídas de contenedores | `collectors/docker_events_collector.py` | por evento |
| `survey.csv` | respuestas de la encuesta final | `form.html` y `/api/survey` | 1/encuestado |
| tablas del escenario | dispositivos y dominios (Esc1), capturas y clics (Esc2), ataque (Esc3) | `fetch_export_state.py` y `/api/export_state` | al cerrar |
| `events.csv` | anotaciones del operador, incluidos los tiempos cronometrados | `session.sh` | discreto |

La concurrencia se lee del router, es decir, de los equipos reales conectados, no con carga sintética.

## Qué hace `session.sh`

Los botones de la consola ejecutan `session.sh` en el Pi por SSH. `session.sh` arranca y detiene todos
los medidores, que corren en el Pi y comparten su reloj, y al cerrar reúne la carpeta de la sesión. Trae
una comprobación que aborta si se ejecuta fuera del Pi, porque la recolección debe hacerse en el servidor
y no en la laptop.

Quien prefiera la línea de comandos puede usarlo directo en el Pi, con el escenario ya levantado.

```bash
./session.sh start esc1     # arranca los medidores
./session.sh status         # medidores activos y filas por archivo
./session.sh end            # cierra la sesión y exporta las tablas
```

O dispararlo desde la laptop, que además descarga la carpeta al terminar.

```powershell
cd metricas\gateway
.\session.ps1 start esc1
.\session.ps1 end
```

`PI_PASS` y `ROUTER_PASS` se leen del `.env` de esta carpeta.

## Análisis

Las gráficas y tablas del capítulo de Resultados se producen fuera de este repositorio, a partir de los
CSV de cada sesión. Aquí vive la parte de recolección, y el análisis se hace por separado con esos archivos.

## Estructura

```
metricas/
├── README.md
├── session.sh                 # coordina la recolección en el Pi (lo ejecutan los botones de la consola)
├── requirements.txt
├── gateway/
│   └── session.ps1            # dispara la sesión desde la laptop y descarga la carpeta
├── pi/
│   ├── collect_resources.py   # recursos del servidor
│   └── install.sh             # instala el medidor de recursos en el Pi
├── collectors/                # medidores que corren en el Pi
│   ├── collect_router.py      # tráfico, equipos y recursos del router
│   ├── target_health_probe.py # disponibilidad del servidor víctima (Esc3)
│   ├── docker_events_collector.py
│   └── fetch_export_state.py  # tablas de cada escenario
├── survey/
│   ├── survey_template.json   # encuesta (editable sin tocar código)
│   └── form.html
├── config/{esc1,esc2,esc3}.yaml
└── sessions/                  # salidas por sesión (no versionadas)
```

El medidor de latencia (`metrics_middleware.js`) vive dentro de cada escenario, no aquí.
