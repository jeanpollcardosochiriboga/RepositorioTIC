# Consola del operador (Node-RED en el Pi)

Wizard de operación de una sola página para encender / apagar los 3 escenarios y
manejar la sesión de métricas, sin abrir terminal. **Corre en el Pi**: con solo
encender el Pi la consola queda lista y el operador la abre desde el navegador del
celular/tablet/PC. No requiere ninguna otra máquina.

## Topología

```
Pi 192.168.1.10  (network_mode: host)
  └── Docker: ops-console (Node-RED) :1880
        │ exec → ssh → 192.168.1.10 (el propio Pi)
        ├── docker compose up/down esc{1,2,3}
        └── session.sh start/end   (medidores de métricas, todo en el Pi)
```

Como los comandos SSH apuntan a `192.168.1.10`, desde el propio Pi se disparan a
sí mismo y `session.sh` corre en el Pi.

## Levantar (en el Pi)

```bash
cd infraestructura/consola
docker compose up -d --build
```

Dashboard: <http://192.168.1.10:1880/ui/>  
Editor:    <http://192.168.1.10:1880/>

`restart: unless-stopped` + Docker habilitado al boot → **la consola arranca sola
al encender el Pi** (incluso tras un corte de luz). Habilitar Docker al boot una
sola vez: `sudo systemctl enable docker`.

## La página (una sola pestaña "Demo")

### 1. Escenario

| Botón | Acción |
|---|---|
| **INICIAR DEMO ESC1/2/3** (azul) | Apaga los otros dos, levanta el elegido, muestra `docker ps` |
| **PANIC: APAGAR TODO** (rojo) | `docker compose down` en los 3 escenarios |
| **Refrescar estado** | Muestra qué contenedores siguen vivos |

### 2. Métricas (solo 2 botones)

| Botón | Acción |
|---|---|
| **INICIAR METRICAS** (verde) | Autodetecta el escenario que esté arriba (`docker ps`) y corre `session.sh start <esc>` en el Pi |
| **TERMINAR METRICAS** (rojo) | `session.sh end`, cierra medidores y corre `export_state` en el Pi |

El operador no elige escenario, primero pulsa **INICIAR DEMO EscN**, luego
**INICIAR METRICAS** (toma el que esté corriendo) y al final **TERMINAR METRICAS**.

Los CSV de la sesión quedan en el Pi en
`tesis_metrics_repo/sessions/<fecha>_<escenario>/`.

## Los escenarios NO sobreviven a un reinicio del Pi

Si el Pi se apaga por un corte de luz y vuelve, **ningún escenario debe quedar
levantado por sí solo**, únicamente la consola. Esto se controla con la
política `restart` de Docker, que al arrancar el daemon solo relevanta los
contenedores `always`/`unless-stopped`:

| Componente | `restart` | Al encender el Pi |
|---|---|---|
| ops-console | `unless-stopped` | se levanta solo ✓ |
| esc1 / esc2 / esc3 | `"no"` | NO se levantan solos ✓ |

`restart: "no"` está puesto en **todos** los servicios del `docker-compose.yml` de
cada escenario en el Pi (incluidos los 4 contenedores de Esc3).

## Cambiar la UI

Toda la UI se construye desde `build_flows.py`. Editar ese script y regenerar:

```bash
python3 build_flows.py
docker compose restart
```

No editar `data/flows.json` a mano, se sobrescribe en cada build.

## Cómo se autentica al Pi

La build incluye `openssh-client` y `sshpass`. El contenedor monta una llave
ed25519 en `/usr/src/node-red/.ssh/` (read-only), ya autorizada para `raspberry1`
en el Pi. Como es una conexión al propio Pi (loopback), el SSH usa
`UserKnownHostsFile=/dev/null` para no depender de `known_hosts` con el montaje
read-only.

## Seguridad

- `data/ssh/` está gitignored: la llave privada nunca debe llegar al repo.
- Con `network_mode: host` la consola escucha en `0.0.0.0:1880`, accesible desde la
  LAN. Si el venue no es de confianza, restringir vía firewall del Pi.
- No requiere auth de Node-RED; el control de la demo es del operador en la LAN.
