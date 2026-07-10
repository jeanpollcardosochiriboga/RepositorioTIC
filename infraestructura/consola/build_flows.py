#!/usr/bin/env python3
"""Generates ops-console/data/flows.json. Run after editing this file.

Una sola pagina 'Demo' pensada para que el operador haga pasos minimos:
  1. Escenario : INICIAR DEMO Esc1/2/3, PANIC (apagar todo), refrescar estado.
  2. Metricas  : solo 2 botones -> INICIAR METRICAS (autodetecta el escenario
                 activo) y TERMINAR METRICAS. No hay boton de despliegue: el
                 tiempo de montaje/despliegue se mide a mano (cronometro + ping).

La consola corre EN EL PI (ver docker-compose.pi.yml). Como los comandos SSH
apuntan a 192.168.1.10, desde el propio Pi se disparan a si mismo y session.sh
sigue corriendo en el Pi igual que antes.
"""
from __future__ import annotations
import json
from pathlib import Path

PI = "raspberry1@192.168.1.10"
KEY = "/usr/src/node-red/.ssh/id_ed25519"
# SSH al propio Pi (loopback). UserKnownHostsFile=/dev/null + LogLevel=ERROR evitan
# el ruido de "known_hosts read-only" (la llave va montada read-only) y dejan el panel
# "Ultimo comando" limpio. Sin riesgo de MITM al ser una conexion a si mismo.
SSH = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=8 -i {KEY} {PI}"
COMPOSE = {
    "esc1": "/home/raspberry1/tesis_escenario1/docker-compose.yml",
    "esc2": "/home/raspberry1/tesis_escenario2/docker-compose.yml",
    "esc3": "/home/raspberry1/tesis_escenario3/docker-compose.yml",
}
# Repo del harness de metricas en el Pi. Los botones de metricas disparan
# session.sh aqui por SSH; la medicion corre 100% en el Pi (la consola solo dispara).
REPO = "/home/raspberry1/tesis_metrics_repo"


def start_only(scenario: str) -> str:
    other = [s for s in COMPOSE if s != scenario]
    parts = [f"docker compose -f {COMPOSE[s]} down" for s in other]
    parts.append(f"docker compose -f {COMPOSE[scenario]} up -d")
    parts.append("sleep 2; docker ps --format '{{.Names}}'")
    return f"{SSH} \"" + " ; ".join(parts) + "\""


def stop_all() -> str:
    parts = [f"docker compose -f {COMPOSE[s]} down" for s in COMPOSE]
    parts.append("docker ps --format '{{.Names}}'")
    return f"{SSH} \"" + " ; ".join(parts) + "\""


def status() -> str:
    return f"{SSH} \"docker ps --format '{{{{.Names}}}}: {{{{.Status}}}}'\""


# Sesion de metricas (session.sh corre EN EL PI) ----------------------------

def sess_start_auto() -> str:
    # Detecta el escenario activo desde los nombres de contenedor en el Pi
    # (esc1-*, jp-esc2-*, esc3-*) y dispara session.sh start <esc>. El \$ va
    # escapado para que la sustitucion ocurra en el Pi, no en el contenedor de
    # la consola. Si no hay escenario arriba, avisa en vez de fallar.
    remote = (
        "scn=\\$(docker ps --format '{{.Names}}' | grep -oE 'esc[123]' | head -1); "
        "if [ -n \\\"\\$scn\\\" ]; then cd " + REPO + " && ./session.sh start \\\"\\$scn\\\"; "
        "else echo 'No hay escenario activo: inicia una demo primero.'; fi"
    )
    return f'{SSH} "{remote}"'


def sess_end() -> str:
    return f'{SSH} "cd {REPO} && ./session.sh end"'


# Node templates ------------------------------------------------------------

def tab(node_id, label, order):
    return {"id": node_id, "type": "tab", "label": label, "disabled": False,
            "info": "", "env": []}


def ui_tab(node_id, name, order, icon="dashboard"):
    return {"id": node_id, "type": "ui_tab", "name": name, "icon": icon,
            "order": order, "disabled": False, "hidden": False}


def ui_group(node_id, name, tab_id, order, width=12):
    return {"id": node_id, "type": "ui_group", "name": name, "tab": tab_id,
            "order": order, "disp": True, "width": str(width),
            "collapse": False, "className": ""}


def ui_button(node_id, group, label, color, bgcolor, payload, order=1, width=4, height=2, wire_to=None):
    # Each button is wired to its own dedicated exec node (id = btn_id + '_exec'),
    # normalmente a traves de un "gate" (btn_id + '_gate') que aplica el lock de
    # "una accion a la vez". El exec tiene el comando baked-in para evitar las
    # trampas de quoting de pasar comandos por msg.payload.
    target = wire_to or f"{node_id}_exec"
    return {
        "id": node_id, "type": "ui_button", "z": "demo_tab", "name": label,
        "group": group, "order": order, "width": str(width), "height": str(height),
        "passthru": False, "label": label, "tooltip": "",
        "color": color, "bgcolor": bgcolor, "className": "",
        "icon": "", "payload": "", "payloadType": "str",
        "topic": label, "topicType": "str",
        "wires": [[target]]
    }


def gate_node(node_id):
    # Lock "una accion a la vez": si ya hay un comando corriendo (ops_busy),
    # bloquea el toque y avisa "Procesando..."; si no, marca ocupado y deja pasar.
    # Asi un doble-pulsado o un orden equivocado no lanza comandos en paralelo.
    return {
        "id": f"{node_id}_gate", "type": "function", "z": "demo_tab",
        "name": f"gate {node_id}",
        "func": (
            "if (flow.get('ops_busy')) {\n"
            "    return [null, { payload: '\\u23f3 Procesando la accion anterior, espera unos segundos...' }];\n"
            "}\n"
            "flow.set('ops_busy', true);\n"
            "return [msg, null];\n"
        ),
        "outputs": 2, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
        "wires": [[f"{node_id}_exec"], ["busy_notice"]]
    }


def button_exec_node(node_id, name, cmd, timer=30):
    # timer (s) acota cuanto puede correr el comando. Los botones de metricas usan
    # 180 porque session.sh start/end (rotacion de CSV + export_state) supera 30 s.
    # La 3a salida (codigo de retorno) SIEMPRE dispara al cerrar el proceso ->
    # libera el lock (clear_busy) aunque el comando no imprima nada en stdout.
    return {
        "id": f"{node_id}_exec", "type": "exec", "z": "demo_tab",
        "name": name, "command": cmd, "addpay": "", "append": "",
        "useSpawn": "false", "timer": str(timer), "winHide": False, "oldrc": False,
        "wires": [["fmt_out", "fmt_status"], [], ["clear_busy"]]
    }


def ui_template(node_id, group, name, content, format_html, order=1, width=12, height=4):
    return {
        "id": node_id, "type": "ui_template", "z": "demo_tab",
        "group": group, "name": name, "order": order,
        "width": str(width), "height": str(height),
        "format": format_html, "storeOutMessages": False,
        "fwdInMessages": True, "resendOnRefresh": True,
        "templateScope": "local", "className": "", "wires": [[]]
    }


# Build the flow ----------------------------------------------------------

def build():
    nodes = []

    # Una sola pagina (admin tab + ui_tab). ui_base lo auto-crea node-red-dashboard
    # en el primer arranque (incluirlo aqui dispara un circular-dep en v3.6.6).
    nodes.append(tab("demo_tab", "Demo (wizard)", 1))
    nodes.append(ui_tab("ui_demo", "Demo", 1, icon="play_arrow"))

    # Grupos (orden: cabecera -> tarjeta de estado arriba -> botones -> metricas -> mensajes)
    nodes.append(ui_group("g_demo_header",  "",               "ui_demo", 1, width=12))
    nodes.append(ui_group("g_demo_status",  "Estado actual",  "ui_demo", 2, width=12))
    nodes.append(ui_group("g_demo_btns",    "1. Escenario",   "ui_demo", 3, width=12))
    nodes.append(ui_group("g_demo_metrics", "2. Metricas",    "ui_demo", 4, width=12))
    nodes.append(ui_group("g_demo_out",     "Mensajes",       "ui_demo", 5, width=12))

    # Tema "Clean Tech" forzado con un <style> ESTATICO. GOTCHA aprendido: una
    # plantilla GLOBAL sin grupo NO renderiza su <style> ni ejecuta su <script> de
    # forma fiable -> el tema no se aplicaba. En cambio, una plantilla CON grupo SI
    # se renderiza ($compile la respeta), y un <style> dentro aplica a TODO el
    # dashboard (el CSS es global por naturaleza). Por eso embebemos el tema en la
    # cabecera (que siempre se ve). Oculta la toolbar azul default (usamos la nuestra).
    theme_style = (
        "<style>"
        "html,body{background-color:#f8fafc !important;}"
        "body,.nr-dashboard-theme,.md-button,.nr-dashboard-cardtitle{font-family:'Segoe UI',sans-serif !important;}"
        "md-toolbar.nr-dashboard-toolbar{display:none !important;}"
        ".nr-dashboard-cardpanel{background:#ffffff !important;border-radius:12px !important;"
        "box-shadow:0 5px 25px rgba(0,0,0,0.05) !important;border:1px solid rgba(0,0,0,0.05) !important;}"
        ".nr-dashboard-cardpanel md-card{background:transparent !important;box-shadow:none !important;border:none !important;}"
        ".nr-dashboard-cardtitle{color:#1e293b !important;font-weight:800 !important;letter-spacing:.3px;}"
        ".nr-dashboard-cardpanel .md-button{border-radius:6px !important;font-weight:700 !important;letter-spacing:.3px;}"
        "</style>"
    )

    # Cabecera con el gradiente Clean Tech (lleva embebido el <style> del tema).
    nodes.append(ui_template(
        "hdr_banner", "g_demo_header", "cabecera", "",
        (theme_style +
         "<div style=\"background:linear-gradient(90deg,#ffffff 0%,#f1f5f9 100%);"
         "border-bottom:3px solid #0ea5e9;box-shadow:0 4px 15px rgba(0,0,0,0.05);"
         "border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:12px;"
         "font-family:'Segoe UI',sans-serif\">"
         "<span style=\"font-size:26px\">&#9881;&#65039;</span>"
         "<div><div style=\"font-size:20px;font-weight:800;color:#1e293b\">Consola del Operador</div>"
         "<div style=\"font-size:12px;color:#64748b;font-family:monospace\">"
         "Tesis &#8212; escenarios de seguridad &#183; Pi 192.168.1.10</div></div>"
         "</div>"),
        order=1, width=12, height=2))

    # Traduce la salida cruda del comando a un mensaje amigable (nada tecnico):
    # el operador solo aprieta botones, no debe ver volcados de docker/ssh.
    nodes.append({
        "id": "fmt_out", "type": "function", "z": "demo_tab",
        "name": "mensaje amigable",
        "func": (
            "const raw = (msg.payload || '').toString();\n"
            "let m;\n"
            "if (/No hay escenario activo/.test(raw)) m = '\\u26a0\\ufe0f Primero inicia un escenario.';\n"
            "else if (/Ya estas midiendo/.test(raw)) m = '\\u2139\\ufe0f Ya estabas midiendo ese escenario.';\n"
            "else if (/Hay una medicion activa/.test(raw)) m = '\\u26a0\\ufe0f Termina la medicion anterior primero (TERMINAR).';\n"
            "else if (/No hay ninguna medicion activa/.test(raw)) m = '\\u2139\\ufe0f No habia ninguna medicion activa.';\n"
            "else if (/Ya hay un arranque en curso/.test(raw)) m = '\\u23f3 Procesando, espera unos segundos...';\n"
            "else if (/\\[end\\]|session closed/.test(raw)) m = '\\u2705 Medicion terminada. Datos guardados en el Pi.';\n"
            "else if (/\\[start\\]|session active/.test(raw)) m = '\\u2705 Medicion iniciada.';\n"
            "else m = '\\u2705 Listo.';\n"
            "const ts = new Date().toLocaleTimeString();\n"
            "return { payload: m + '   (' + ts + ')' };\n"
        ),
        "outputs": 1, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
        "wires": [["txt_demo_out"]]
    })

    # Tarjeta de estado: detecta el escenario activo del 'docker ps'. Si la salida
    # NO es un docker ps (p.ej. mensajes de metricas), no toca la tarjeta
    # (return null) para no mostrar "apagado" por error.
    nodes.append({
        "id": "fmt_status", "type": "function", "z": "demo_tab",
        "name": "tarjeta de estado",
        "func": (
            "const out = (msg.payload || '').toString();\n"
            "if (!/tesis-ops-console|esc[123]-|jp-esc2-/.test(out)) return null;\n"
            "let scn = null;\n"
            "if (/(^|\\n)\\s*esc1-/.test(out)) scn = 'esc1';\n"
            "else if (/(^|\\n)\\s*(jp-)?esc2-/.test(out)) scn = 'esc2';\n"
            "else if (/(^|\\n)\\s*esc3-/.test(out)) scn = 'esc3';\n"
            "const map = {\n"
            "  esc1: { label: 'ESCENARIO 1  \\u2014  EN VIVO', color: '#0284c7' },\n"
            "  esc2: { label: 'ESCENARIO 2  \\u2014  EN VIVO', color: '#0284c7' },\n"
            "  esc3: { label: 'ESCENARIO 3  \\u2014  EN VIVO', color: '#0284c7' }\n"
            "};\n"
            "const card = scn ? map[scn] : { label: 'TODO APAGADO', color: '#64748b' };\n"
            "return { payload: card };\n"
        ),
        "outputs": 1, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
        "wires": [["card_status"]]
    })

    # Lock "una accion a la vez": busy_notice avisa en la linea de Mensajes cuando
    # se pulsa estando ocupado; clear_busy libera el lock al cerrar cada comando.
    nodes.append({
        "id": "busy_notice", "type": "function", "z": "demo_tab", "name": "busy notice",
        "func": "return { payload: (msg.payload || '').toString() };\n",
        "outputs": 1, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
        "wires": [["txt_demo_out"]]
    })
    nodes.append({
        "id": "clear_busy", "type": "function", "z": "demo_tab", "name": "clear busy",
        "func": "flow.set('ops_busy', false);\nreturn null;\n",
        "outputs": 1, "noerr": 0, "initialize": "", "finalize": "", "libs": [],
        "wires": [[]]
    })

    # Tarjeta de estado grande y amigable (ui_template enlaza msg.payload {label,color}).
    nodes.append(ui_template(
        "card_status", "g_demo_status", "tarjeta estado", "",
        ("<div ng-style=\"{'background': (msg.payload.color || '#607d8b')}\" "
         "style=\"border-radius:12px;padding:22px;text-align:center;color:#fff;"
         "font-weight:800;font-size:26px;letter-spacing:.5px;"
         "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif\">"
         "{{msg.payload.label || 'Cargando estado...'}}"
         "</div>"),
        order=1, width=12, height=3))

    # Linea de mensajes amigables (resultado de la ultima accion / aviso de lock).
    nodes.append({
        "id": "txt_demo_out", "type": "ui_text", "z": "demo_tab",
        "group": "g_demo_out", "order": 1, "width": "12", "height": "2",
        "name": "mensaje", "label": "", "format": "<div style='font-size:16px;padding:6px 2px'>{{msg.payload}}</div>",
        "layout": "row-spread", "className": ""
    })

    # Al arrancar, pinta la tarjeta con el estado real (sin esperar a que pulsen).
    nodes.append({
        "id": "startup_status", "type": "inject", "z": "demo_tab", "name": "al arrancar",
        "props": [{"p": "payload"}], "repeat": "", "crontab": "", "once": True, "onceDelay": "3",
        "topic": "", "payload": "", "payloadType": "str",
        "wires": [["btn_demo_status_exec"]]
    })

    def add_button(node_id, group, label, color, bgcolor, cmd, order, w, h, timer=30, gated=True):
        # gated=True -> el toque pasa por el gate (lock una-accion-a-la-vez).
        # gated=False -> va directo al exec (PANIC: emergencia, siempre inmediato).
        target = f"{node_id}_gate" if gated else f"{node_id}_exec"
        nodes.append(ui_button(node_id, group, label, color, bgcolor, "",
                               order=order, width=w, height=h, wire_to=target))
        if gated:
            nodes.append(gate_node(node_id))
        nodes.append(button_exec_node(node_id, label, cmd, timer=timer))

    # ---- 1. Escenario ---- (paleta Clean Tech: azul #0284c7, rojo #dc2626, slate #64748b)
    add_button("btn_demo_e1",    "g_demo_btns", "INICIAR DEMO ESC1",   "#fff", "#0284c7", start_only("esc1"), 1, 4, 3)
    add_button("btn_demo_e2",    "g_demo_btns", "INICIAR DEMO ESC2",   "#fff", "#0284c7", start_only("esc2"), 2, 4, 3)
    add_button("btn_demo_e3",    "g_demo_btns", "INICIAR DEMO ESC3",   "#fff", "#0284c7", start_only("esc3"), 3, 4, 3)
    # PANIC sin gate: el apagado de emergencia debe responder aunque haya algo en curso.
    add_button("btn_demo_panic", "g_demo_btns", "PANIC: APAGAR TODO",  "#fff", "#dc2626", stop_all(),         4, 12, 2, gated=False)
    add_button("btn_demo_status","g_demo_btns", "Refrescar estado",    "#fff", "#64748b", status(),           5, 12, 1)

    # ---- 2. Metricas (solo 2 botones; disparan session.sh EN EL PI; timer 180 s) ----
    add_button("btn_met_start", "g_demo_metrics", "INICIAR METRICAS",  "#fff", "#059669", sess_start_auto(), 1, 6, 2, timer=180)
    add_button("btn_met_end",   "g_demo_metrics", "TERMINAR METRICAS", "#fff", "#dc2626", sess_end(),        2, 6, 2, timer=180)

    # (La explicacion de metricas y la ubicacion de los CSV viven en el README,
    # no en el panel del operador: aqui solo botones y estado.)

    return nodes


if __name__ == "__main__":
    flows = build()
    out = Path(__file__).parent / "data" / "flows.json"
    out.write_text(json.dumps(flows, indent=4, ensure_ascii=False))
    print(f"wrote {out} ({len(flows)} nodes)")
