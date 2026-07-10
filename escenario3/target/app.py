import time
import os
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
START_TIME = time.time()

INDEX_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sistema de Gestión Transporte Institucional</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    .landing-page {
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      font-family: 'Inter', sans-serif;
      animation: gradientShift 15s ease infinite;
    }
    @keyframes gradientShift {
      0%, 100% { background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%); }
      50%       { background: linear-gradient(135deg, #f093fb 0%, #667eea 50%, #764ba2 100%); }
    }
    .landing-overlay {
      position: absolute; top: 0; left: 0; right: 0; bottom: 0;
      background:
        radial-gradient(circle at 20% 50%, rgba(120,119,198,0.3), transparent 50%),
        radial-gradient(circle at 80% 80%, rgba(255,119,198,0.3), transparent 50%),
        radial-gradient(circle at 40% 20%, rgba(138,119,255,0.3), transparent 50%);
      animation: overlayPulse 8s ease-in-out infinite;
    }
    @keyframes overlayPulse {
      0%, 100% { opacity: 0.6; }
      50%       { opacity: 0.9; }
    }
    .landing-content {
      position: relative; z-index: 1; text-align: center;
      padding: 2rem; max-width: 1200px; width: 100%;
      animation: fadeInUp 1s ease-out;
    }
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(30px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .landing-logo-container {
      margin-bottom: 2rem; display: flex; justify-content: center;
      animation: floatAnimation 3s ease-in-out infinite;
    }
    @keyframes floatAnimation {
      0%, 100% { transform: translateY(0); }
      50%       { transform: translateY(-10px); }
    }
    .landing-logo-circle {
      width: 120px; height: 120px;
      background: rgba(255,255,255,0.2); backdrop-filter: blur(10px);
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      box-shadow: 0 8px 32px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.2);
      border: 1px solid rgba(255,255,255,0.3); transition: all 0.3s ease;
    }
    .landing-logo-circle:hover {
      transform: scale(1.05);
      box-shadow: 0 12px 48px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.3);
    }
    .bus-icon { width: 60px; height: 60px; color: white; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1)); }
    .landing-title {
      font-size: 3.5rem; font-weight: 800; color: white; margin-bottom: 1rem;
      line-height: 1.2; text-shadow: 0 2px 20px rgba(0,0,0,0.3);
      animation: fadeInUp 1s ease-out 0.2s backwards;
    }
    .landing-title-accent {
      background: linear-gradient(90deg, #fff, #f0f0f0);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
      display: inline-block;
    }
    .landing-description {
      font-size: 1.25rem; color: rgba(255,255,255,0.9); margin-bottom: 3rem;
      font-weight: 300; max-width: 600px; margin-left: auto; margin-right: auto;
      animation: fadeInUp 1s ease-out 0.4s backwards;
    }
    .landing-features {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 2rem; margin-bottom: 3rem; max-width: 900px;
      margin-left: auto; margin-right: auto;
    }
    .feature-card {
      background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
      border-radius: 16px; padding: 2rem; border: 1px solid rgba(255,255,255,0.2);
      transition: all 0.3s ease; animation: fadeInUp 1s ease-out 0.6s backwards;
    }
    .feature-card:nth-child(2) { animation-delay: 0.7s; }
    .feature-card:nth-child(3) { animation-delay: 0.8s; }
    .feature-card:hover {
      transform: translateY(-8px); background: rgba(255,255,255,0.15);
      box-shadow: 0 12px 32px rgba(0,0,0,0.2);
    }
    .feature-icon { font-size: 3rem; margin-bottom: 1rem; }
    .feature-card h3 { color: white; font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem; }
    .feature-card p  { color: rgba(255,255,255,0.8); font-size: 0.95rem; font-weight: 300; margin: 0; }

    .landing-cta-button {
      background: white; color: #667eea; border: none;
      padding: 1rem 3rem; font-size: 1.1rem; font-weight: 600;
      border-radius: 50px; cursor: pointer;
      display: inline-flex; align-items: center; gap: 0.75rem;
      transition: all 0.3s ease; box-shadow: 0 8px 24px rgba(0,0,0,0.2);
      font-family: 'Inter', sans-serif;
      animation: fadeInUp 1s ease-out 0.9s backwards, pulse 2s ease-in-out 2s infinite;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50%       { transform: scale(1.05); }
    }
    .landing-cta-button:hover {
      transform: translateY(-2px) scale(1.05); box-shadow: 0 12px 32px rgba(0,0,0,0.3);
      animation: none;
    }
    .landing-cta-button:active { transform: translateY(0) scale(1.02); }
    .landing-cta-button:disabled { opacity: 0.7; cursor: not-allowed; animation: none; }
    .button-arrow { width: 20px; height: 20px; transition: transform 0.3s ease; }
    .landing-cta-button:hover .button-arrow { transform: translateX(4px); }

    .spinner {
      width: 20px; height: 20px; border: 2px solid #667eea;
      border-top-color: transparent; border-radius: 50%;
      animation: spin 0.7s linear infinite; display: none;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    #msg {
      margin-top: 1.2rem; font-size: 1rem; font-weight: 500; min-height: 1.4rem;
      color: rgba(255,255,255,0.95); text-shadow: 0 1px 6px rgba(0,0,0,0.3);
    }

    .landing-footer {
      margin-top: 4rem; padding-top: 2rem; border-top: 1px solid rgba(255,255,255,0.2);
      animation: fadeInUp 1s ease-out 1s backwards;
    }
    .landing-footer p { color: rgba(255,255,255,0.7); font-size: 0.9rem; font-weight: 300; margin: 0; }

    @media (max-width: 768px) {
      .landing-title { font-size: 2.5rem; }
      .landing-description { font-size: 1rem; }
      .landing-features { grid-template-columns: 1fr; gap: 1.5rem; }
      .landing-cta-button { padding: 0.875rem 2rem; font-size: 1rem; }
    }
    @media (max-width: 480px) {
      .landing-title { font-size: 2rem; }
      .landing-logo-circle { width: 100px; height: 100px; }
      .bus-icon { width: 50px; height: 50px; }
    }
  </style>
</head>
<body>
  <div class="landing-page">
    <div class="landing-overlay"></div>
    <div class="landing-content">

      <div class="landing-logo-container">
        <div class="landing-logo-circle">
          <svg class="bus-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 16C4 16.88 4.39 17.67 5 18.22V20C5 20.55 5.45 21 6 21H7C7.55 21 8 20.55 8 20V19H16V20C16 20.55 16.45 21 17 21H18C18.55 21 19 20.55 19 20V18.22C19.61 17.67 20 16.88 20 16V6C20 2.5 16.42 2 12 2C7.58 2 4 2.5 4 6V16ZM7.5 17C6.67 17 6 16.33 6 15.5C6 14.67 6.67 14 7.5 14C8.33 14 9 14.67 9 15.5C9 16.33 8.33 17 7.5 17ZM16.5 17C15.67 17 15 16.33 15 15.5C15 14.67 15.67 14 16.5 14C17.33 14 18 14.67 18 15.5C18 16.33 17.33 17 16.5 17ZM6 11V6H18V11H6Z" fill="currentColor"/>
          </svg>
        </div>
      </div>

      <h1 class="landing-title">
        Sistema de Gestión<br>
        <span class="landing-title-accent">Transporte Institucional</span>
      </h1>

      <p class="landing-description">
        Administra rutas, conductores, unidades y reportes de manera eficiente
      </p>

      <div class="landing-features">
        <div class="feature-card">
          <div class="feature-icon">🚌</div>
          <h3>Gestión de Rutas</h3>
          <p>Control completo de rutas y paradas</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">👥</div>
          <h3>Conductores</h3>
          <p>Administración de personal y unidades</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h3>Reportes</h3>
          <p>Análisis y seguimiento en tiempo real</p>
        </div>
      </div>

      <button class="landing-cta-button" id="loginBtn" onclick="ingresar()">
        <span class="spinner" id="spinner"></span>
        <span id="btnText">Ingresar al Sistema</span>
        <svg class="button-arrow" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <div id="msg"></div>

      <div class="landing-footer">
        <p>© 2025 Sistema de Transporte Institucional</p>
      </div>

    </div>
  </div>

  <script>
    function ingresar() {
      var btn = document.getElementById('loginBtn');
      var spinner = document.getElementById('spinner');
      var btnText = document.getElementById('btnText');
      var msg = document.getElementById('msg');

      btn.disabled = true;
      spinner.style.display = 'block';
      btnText.textContent = 'Autenticando...';
      msg.textContent = '';

      fetch('/reservar', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          msg.textContent = '✅ Acceso concedido. Bienvenido al sistema.';
          msg.style.color = '#a7f3d0';
        })
        .catch(function() {
          msg.textContent = '❌ Error: servidor no disponible. Intente nuevamente.';
          msg.style.color = '#fca5a5';
        })
        .finally(function() {
          btn.disabled = false;
          spinner.style.display = 'none';
          btnText.textContent = 'Ingresar al Sistema';
        });
    }
  </script>
</body>
</html>"""


@app.route('/')
def index():
    return render_template_string(INDEX_HTML)


@app.route('/reservar', methods=['POST'])
def reservar():
    time.sleep(0.2)
    return jsonify({'status': 'ok', 'message': 'Acceso concedido'})


@app.route('/health')
def health():
    uptime = round(time.time() - START_TIME, 1)
    return jsonify({'status': 'ok', 'uptime': uptime})


if __name__ == '__main__':
    # Cola de escucha (backlog) pequeña: bajo flood el backlog se mantiene acotado,
    # así el target se cae de forma visible PERO se recupera en pocos segundos cuando
    # el proxy (rate-limit 1 r/s) corta el ingreso. Con el backlog por defecto (128)
    # el target acumulaba una cola gigante que tardaba minutos en drenar y la
    # recuperación no se apreciaba en la demo ni en target_health.csv.
    from werkzeug.serving import BaseWSGIServer
    BaseWSGIServer.request_queue_size = 12
    app.run(host='0.0.0.0', port=5000, threaded=False, debug=False)
