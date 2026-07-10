# Infraestructura

Componentes que sostienen la red del laboratorio, comunes a los tres escenarios.

## `ics/` — Uso compartido de Internet en el gateway Windows

El gateway del laboratorio es una laptop con Windows que comparte su conexión Wi-Fi hacia el puerto
Ethernet mediante el uso compartido de Internet (Internet Connection Sharing, ICS). Así el router
OpenWrt recibe salida a Internet por su WAN.

- `reapply-ics.ps1` — vuelve a enlazar el adaptador público con el privado. Como ICS no se re-comparte
  solo tras reiniciar, se ejecuta al arranque desde una tarea programada (SYSTEM). Deja registro en
  `C:\gateway\ics.log`.
- `setup-gateway.ps1` — instalador de una sola vez: deja el adaptador Wi-Fi en autoconexión, crea la
  tarea programada `ReapplyICS` y deshabilita adaptadores virtuales que confunden a ICS.
- `fix-wifi.ps1` — reinicia el adaptador Wi-Fi cuando queda asociado pero sin dirección IPv4 (APIPA).

## `consola/` — Consola del operador

Panel de Node-RED que se levanta en el propio Pi (`network_mode: host`) y desde el que el operador
dispara acciones por SSH al Pi y al router. Se despliega con Docker:

```bash
cd infraestructura/consola
docker compose up -d --build   # panel en http://192.168.1.10:1880/ui/
```

Requisito previo: colocar la llave privada ed25519 del operador en `consola/data/ssh/`
(`id_ed25519`, `id_ed25519.pub`, `known_hosts`). No se versiona; su clave pública debe estar autorizada
para `raspberry1` en el Pi.

## Firmware del router

El punto de acceso se levanta con OpenWrt sobre un TP-Link Archer C7 v5. La imagen con la que se flasheó
es `openwrt-24.10.4-ath79-generic-tplink_archer-c7-v5-squashfs-factory.bin`, de la descarga oficial de
OpenWrt. Es un flasheo único de montaje inicial; por su tamaño, el binario se entrega aparte y no se
versiona aquí.

## Instalación de Docker en la Raspberry Pi

Sobre Raspberry Pi OS (Debian 12 Bookworm) el motor de contenedores se instala con el script de
conveniencia oficial:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker "$USER"    # usar docker sin sudo (reiniciar sesión)
```
