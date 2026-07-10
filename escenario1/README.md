# Escenario 1 — Detección de red y clasificación de dominios

Prototipo de ciberseguridad. Panel en tiempo real que detecta los dispositivos de la red local,
observa las consultas DNS que hacen y clasifica los dominios que visitan, todo sobre Node-RED con una
visualización en D3.js. Controla el punto de acceso del router OpenWrt por SSH.

## Qué hace

- **Detección de dispositivos:** descubre los equipos activos de la subred con `nmap`.
- **Mapa de red:** los presenta como un grafo interactivo en D3.js.
- **Consultas DNS:** recibe por syslog (UDP) las consultas que resuelve el router OpenWrt y las muestra
  en vivo.
- **Clasificación de dominios:** agrupa los dominios visitados por servicio para leer de un vistazo qué
  se está usando en la red.
- **Corte del punto de acceso:** enciende y apaga el AP WiFi del router por SSH, lo que desengancha a
  los dispositivos cuando hace falta reiniciar un grupo. No es un cortafuegos: solo apaga el AP.
- **Códigos QR:** genera el QR de acceso al panel y el QR de la red WiFi de forma dinámica.

## Requisitos

- Docker y Docker Compose.
- Un router **OpenWrt** en la red local con SSH habilitado.
- El contenedor necesita permisos de red de bajo nivel (`NET_RAW`, `NET_ADMIN`), ya declarados en el
  `docker-compose.yml`, para que `nmap` funcione.

## Despliegue

```bash
git clone https://github.com/jeanpollcardosochiriboga/RepositorioTIC.git
cd RepositorioTIC/escenario1
cp .env.example .env          # completar los valores según la red (ver la tabla siguiente)
docker compose up -d
docker compose logs -f
```

El panel queda en `http://localhost:1881`. El contenedor corre con `network_mode: host` para que `nmap`
vea la red real y para alcanzar al router por SSH.

## Configuración (`.env`)

Toda la configuración vive en un solo archivo `.env`; no hace falta tocar `flows.json`. Los nodos leen
estos valores con `env.get('NOMBRE')`.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `ROUTER_IP` | IP del router OpenWrt | `192.168.1.1` |
| `ROUTER_PASS` | Contraseña SSH del router (usuario `root`) | `tu_password_ssh_del_router` |
| `SUBNET` | Subred a escanear con nmap | `192.168.1.0/24` |
| `MY_PC_IP` | IP del equipo administrador, excluida del mapa | `192.168.1.20` |
| `DASH_IP` | IP del servidor, respaldo del QR si la autodetección falla | `192.168.1.10` |
| `DASH_PORT` | Puerto del panel | `1881` |

Tras cambiar el `.env`, reiniciar el contenedor para que tome los valores nuevos:

```bash
docker compose down && docker compose up -d
```

## Arquitectura

```
escenario1/
├── docker-compose.yml   → servicio con network_mode host y permisos NET_RAW/NET_ADMIN
├── Dockerfile           → Node.js 18 Alpine + nmap + openssh-client + Node-RED
├── flows.json           → lógica del escenario (Node-RED), generada por la herramienta
├── settings.js          → configuración de Node-RED
├── public/
│   ├── images/          → iconos de los dispositivos
│   └── js/d3.v7.min.js  → librería de visualización
└── scripts/
    ├── esc1_apply_openwrt_policy.sh      → apaga el AP WiFi del router (kill-switch)
    └── esc1_rollback_openwrt_policy.sh   → vuelve a encender el AP WiFi
```

## Código QR del panel

El QR se genera en tiempo de ejecución: Node-RED ejecuta `hostname -I` para detectar la IP real del
servidor y, si la detección falla, recurre a `DASH_IP` del `.env`. No hay ninguna imagen que reemplazar.
El QR de la red WiFi también es dinámico: el operador escribe el nombre de la red en el panel y el código
se arma al momento.

## Modificar el flujo (Node-RED)

Los cambios se hacen en el editor visual (`http://localhost:1881/admin`) y se exportan con
**Menú → Export → Download**, que reemplaza `flows.json`. El archivo es sensible al orden, así que no
conviene editarlo a mano.

## Conectividad y red

La salida a Internet del router y la red del laboratorio las provee la infraestructura común (gateway
con uso compartido de Internet). El procedimiento está en
[`../infraestructura/README.md`](../infraestructura/README.md).

## Detener

```bash
docker compose down
```
