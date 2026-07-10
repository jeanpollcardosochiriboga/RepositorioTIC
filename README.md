# Repositorio del prototipo de ciberseguridad

Código del prototipo de la plataforma didáctica de ciberseguridad. Reúne los tres escenarios de
demostración, la infraestructura de red que los sostiene y el sistema de recolección de métricas.
Está pensado para clonarse en una Raspberry Pi y ponerse en marcha con Docker.

## Estructura

| Carpeta | Contenido |
|---|---|
| `infraestructura/` | Uso compartido de Internet (ICS) del gateway Windows, consola del operador y notas de firmware/Docker |
| `escenario1/` | Detección de dispositivos en la red y clasificación de dominios |
| `escenario2/` | Simulación de phishing educativo |
| `escenario3/` | Denegación de servicio controlada (colapso y recuperación) |
| `metricas/` | Recolección de métricas: `session.sh`, medidores y descarga de resultados |

## Topología

```
Internet (Wi-Fi del lugar o tethering)
      │
  Gateway Windows  ── uso compartido de Internet (ICS) ──▶ WAN del router
      │
  Router OpenWrt (TP-Link Archer C7 v5, 192.168.1.1)
      │
  Raspberry Pi (192.168.1.10) ── Node-RED + Docker: un escenario a la vez
```

## Puesta en marcha

Requisitos: Docker y Docker Compose en la Raspberry Pi (ver `infraestructura/README.md`).

```bash
git clone https://github.com/jeanpollcardosochiriboga/RepositorioTIC.git
cd RepositorioTIC/escenario1        # o escenario2 / escenario3
cp .env.example .env                # rellenar los valores reales (ver .env.example)
docker compose up -d --build
```

Se corre **un escenario a la vez** para no agotar la memoria del Pi; detener el anterior con
`docker compose down` antes de arrancar otro. Los paneles quedan en `:1881` (Esc1), `:1882` (Esc2)
y `:1883` (Esc3). La consola del operador (`infraestructura/consola/`) publica su panel en `:1880`.

## Secretos

Cada componente lee sus credenciales de un archivo `.env` que **no se versiona**. Se parte siempre de
`.env.example`, que solo contiene marcadores. Afecta a la contraseña del router (Escenario 1 y métricas),
la contraseña del Pi (métricas), la cuenta de Gmail con su contraseña de aplicación y el token de TMDb
(Escenario 2). La llave SSH de la consola tampoco se versiona: se coloca en `infraestructura/consola/data/ssh/`.
