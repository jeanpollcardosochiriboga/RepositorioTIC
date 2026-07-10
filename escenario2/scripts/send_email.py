#!/usr/bin/env python3
import sys, json, base64, os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "www", "mu1ticines-logo.png")
try:
    with open(LOGO_PATH, "rb") as f:
        LOGO_B64 = base64.b64encode(f.read()).decode()
except FileNotFoundError:
    LOGO_B64 = ""
LOGO_SRC = f"data:image/png;base64,{LOGO_B64}" if LOGO_B64 else ""

def main():
    if len(sys.argv) < 2:
        print("Error: argumento base64 requerido", file=sys.stderr)
        sys.exit(1)

    data        = json.loads(base64.b64decode(sys.argv[1]).decode('utf-8'))
    smtp_user   = os.environ.get('SMTP_USER', '')
    smtp_pass   = os.environ.get('SMTP_PASS', '')
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port   = int(os.environ.get('SMTP_PORT', '465'))
    sender_name = os.environ.get('SENDER_NAME', 'Mu1ticines')
    base_url    = os.environ.get('BASE_URL', 'http://localhost:1882')

    to_email  = data.get('to', '')
    nombre    = data.get('nombre', '')
    movie     = data.get('movie', '')
    time_slot = data.get('timeSlot', '')
    seats     = data.get('seats', '')
    sector    = data.get('sector', '')

    ticket_link = f"{base_url}/tickets?ref={quote(to_email)}&nombre={quote(nombre)}"

    saludo = f"Hola {nombre}," if nombre else "Hola,"

    logo_img = f'<img src="{LOGO_SRC}" alt="Mu1ticines" height="64" style="margin-bottom:10px;display:block;margin-left:auto;margin-right:auto">' if LOGO_SRC else ''
    logo_footer = f'<img src="{LOGO_SRC}" alt="Mu1ticines" width="52" style="display:block">' if LOGO_SRC else ''

    sector_row = f"""
      <tr style="background:#f5f5f5">
        <td style="padding:10px 14px;color:#555">Sede</td>
        <td style="padding:10px 14px;font-weight:bold;color:#111">{sector}</td>
      </tr>""" if sector else ''

    html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:0">
  <div style="background:#17243D;color:#fff;padding:24px;text-align:center">
    {logo_img}
    <h1 style="margin:0;font-size:22px;letter-spacing:1px">MU1TICINES</h1>
    <p style="margin:4px 0 0;font-size:13px;opacity:0.75">Confirmaci&oacute;n de Sorteo</p>
  </div>
  <div style="background:#fff;padding:30px">
    <p style="color:#333;font-size:15px">{saludo} tu participaci&oacute;n en el sorteo ha sido registrada:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px">
      <tr style="background:#f5f5f5">
        <td style="padding:10px 14px;color:#555">Pel&iacute;cula</td>
        <td style="padding:10px 14px;font-weight:bold;color:#111">{movie}</td>
      </tr>
      <tr>
        <td style="padding:10px 14px;color:#555">Horario</td>
        <td style="padding:10px 14px;font-weight:bold;color:#111">{time_slot}</td>
      </tr>
      <tr style="background:#f5f5f5">
        <td style="padding:10px 14px;color:#555">Asientos</td>
        <td style="padding:10px 14px;font-weight:bold;color:#111">{seats}</td>
      </tr>{sector_row}
    </table>
    <div style="text-align:center;margin:28px 0">
      <a href="{ticket_link}"
         style="background:#FFC600;color:#17243D;padding:14px 36px;text-decoration:none;
                border-radius:6px;font-weight:bold;font-size:15px;display:inline-block">
        Ver mis entradas digitales &#8594;
      </a>
    </div>
    <hr style="border:none;border-top:2px solid #17243D;margin:24px 0">
    <table style="width:100%;font-size:12px;color:#444">
      <tr>
        <td style="padding-right:16px;vertical-align:middle;width:64px">
          {logo_footer}
        </td>
        <td style="vertical-align:middle;line-height:1.6">
          <strong style="font-size:13px;color:#17243D">SISTEMA DE RESERVAS MU1TICINES</strong><br>
          <span style="color:#888">Sorteo de Entradas Digitales</span><br>
          <span style="color:#aaa">sorteo@mu1ticines.com.ec</span>
        </td>
      </tr>
    </table>
  </div>
</div>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Tus Entradas de Cine — Confirmación de Sorteo'
    msg['From']    = f'"{sender_name}" <{smtp_user}>'
    msg['To']      = to_email
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_email], msg.as_string())

    print(f"OK: email enviado a {to_email}")

if __name__ == '__main__':
    main()
