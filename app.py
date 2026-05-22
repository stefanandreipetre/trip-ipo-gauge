"""
TRIP Gauge pentru Render.

Rolul acestui app:
1. Serveste pagina publica pe Render.
2. Face fetch server-side catre computerul tau pornit permanent.
3. Returneaza datele catre browser prin /api/data.

Setari necesare in Render, Environment:
HOME_SERVER_URL = https://adresa-ta-publica-sau-tunnel
optional:
HOME_SERVER_TOKEN = acelasi API_KEY configurat pe serverul de acasa
RETAIL_TOTAL = 41750000
FETCH_TIMEOUT = 8
"""

import os
import time
from urllib.parse import urljoin

import requests
from flask import Flask, Response, jsonify

app = Flask(__name__)

RETAIL_TOTAL = int(os.getenv("RETAIL_TOTAL", "41750000"))
HOME_SERVER_URL = os.getenv("HOME_SERVER_URL", "").strip().rstrip("/")
HOME_SERVER_TOKEN = os.getenv("HOME_SERVER_TOKEN", "").strip()
FETCH_TIMEOUT = float(os.getenv("FETCH_TIMEOUT", "8"))
CACHE_SECONDS = float(os.getenv("CACHE_SECONDS", "3"))

_session = requests.Session()
_cache = {
    "at": 0.0,
    "payload": None,
    "error": None,
}


def _home_data_url() -> str:
    if not HOME_SERVER_URL:
        return ""
    return urljoin(HOME_SERVER_URL + "/", "data")


def _fetch_from_home() -> dict:
    url = _home_data_url()
    if not url:
        return {
            "ok": False,
            "subscribed": 0,
            "percentage": 0,
            "timestamp": "—",
            "source": "render",
            "error": "Lipseste HOME_SERVER_URL in Render Environment.",
        }

    headers = {
        "Accept": "application/json",
        "User-Agent": "TRIP-Gauge-Render/1.0",
    }
    if HOME_SERVER_TOKEN:
        headers["X-API-Key"] = HOME_SERVER_TOKEN
        headers["X-TRIP-Token"] = HOME_SERVER_TOKEN

    try:
        r = _session.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        subscribed = int(data.get("subscribed") or data.get("bid_vol") or 0)
        percentage = round((subscribed / RETAIL_TOTAL) * 100, 2) if RETAIL_TOTAL else 0

        return {
            "ok": bool(data.get("ok", True)) and subscribed >= 0,
            "subscribed": subscribed,
            "percentage": percentage,
            "timestamp": data.get("timestamp") or data.get("updated_at") or "—",
            "source": "home_server",
            "home_source": data.get("source", "home"),
            "retail_total": RETAIL_TOTAL,
            "error": data.get("error"),
        }
    except Exception as exc:
        last_payload = _cache.get("payload")
        if last_payload:
            fallback = dict(last_payload)
            fallback["ok"] = False
            fallback["source"] = "render_cache"
            fallback["error"] = f"Nu pot citi serverul de acasa: {exc}"
            return fallback

        return {
            "ok": False,
            "subscribed": 0,
            "percentage": 0,
            "timestamp": "—",
            "source": "render",
            "retail_total": RETAIL_TOTAL,
            "error": f"Nu pot citi serverul de acasa: {exc}",
        }


@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "home_server_configured": bool(HOME_SERVER_URL),
        "home_data_url": _home_data_url() if HOME_SERVER_URL else None,
    })


@app.get("/api/data")
@app.get("/data")
def data():
    now = time.time()
    if _cache["payload"] is not None and now - _cache["at"] < CACHE_SECONDS:
        return jsonify(_cache["payload"])

    payload = _fetch_from_home()
    _cache["payload"] = payload
    _cache["at"] = now
    return jsonify(payload)


@app.get("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html; charset=utf-8")


INDEX_HTML = """<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TRIP IPO Gauge</title>
  <style>
    :root { font-family: Georgia, serif; color: #172033; background: #f1f5f9; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: start center; padding: 18px; }
    .card { width: 100%; max-width: 540px; background: white; border: 1px solid #e2e8f0; border-radius: 22px; box-shadow: 0 6px 28px rgba(15,23,42,.08); overflow: hidden; }
    .head { padding: 18px 20px 14px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .ticker { background: #00aeef; color: white; font: 700 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; padding: 4px 9px; border-radius: 6px; letter-spacing: 2px; }
    .status { font: 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; padding: 4px 10px; border-radius: 999px; border: 1px solid #bbf7d0; background: #f0fdf4; color: #15803d; }
    .status.err { border-color: #fecaca; background: #fef2f2; color: #dc2626; }
    .body { padding: 20px; }
    .label { color: #64748b; font-size: 12px; letter-spacing: .6px; text-transform: uppercase; }
    .value { margin-top: 5px; font: 800 38px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; line-height: 1.05; }
    .bar { margin-top: 18px; height: 12px; border-radius: 999px; background: #e2e8f0; overflow: hidden; }
    .fill { height: 100%; width: 0%; border-radius: inherit; background: linear-gradient(90deg, #00aeef, #f97316); transition: width .7s ease; }
    .grid { margin-top: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
    .box b { display: block; margin-top: 3px; font: 700 16px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .errbox { display: none; margin-top: 14px; padding: 11px 12px; border-radius: 12px; border: 1px solid #fecaca; background: #fef2f2; color: #b91c1c; font-size: 13px; }
    .foot { padding: 10px 20px 14px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 11px; display: flex; justify-content: space-between; gap: 10px; }
  </style>
</head>
<body>
  <main class="card">
    <section class="head">
      <div>
        <div class="ticker">TRIP</div>
        <div style="margin-top:8px;font-size:13px;color:#64748b">Christian Tour IPO Gauge</div>
      </div>
      <div id="status" class="status">LIVE</div>
    </section>

    <section class="body">
      <div class="label">Subscrieri retail estimate din Bid Vol.</div>
      <div id="subscribed" class="value">—</div>
      <div class="bar"><div id="fill" class="fill"></div></div>

      <div class="grid">
        <div class="box"><span class="label">Procent</span><b id="percentage">—</b></div>
        <div class="box"><span class="label">Total retail</span><b id="total">—</b></div>
        <div class="box"><span class="label">Actualizat</span><b id="timestamp">—</b></div>
        <div class="box"><span class="label">Sursa</span><b id="source">—</b></div>
      </div>

      <div id="errbox" class="errbox"></div>
    </section>

    <section class="foot">
      <span>Render proxy</span>
      <span>fetch: /api/data</span>
    </section>
  </main>

  <script>
    const fmt = new Intl.NumberFormat('ro-RO');
    const $ = id => document.getElementById(id);

    async function refresh() {
      try {
        const r = await fetch('/api/data?ts=' + Date.now(), { cache: 'no-store' });
        const data = await r.json();
        const subscribed = Number(data.subscribed || 0);
        const percentage = Number(data.percentage || 0);
        const total = Number(data.retail_total || 41750000);

        $('subscribed').textContent = subscribed ? fmt.format(subscribed) : '—';
        $('percentage').textContent = percentage ? percentage.toFixed(2) + '%' : '—';
        $('total').textContent = fmt.format(total);
        $('timestamp').textContent = data.timestamp || '—';
        $('source').textContent = data.source || '—';
        $('fill').style.width = Math.max(0, Math.min(100, percentage)) + '%';

        if (data.ok && !data.error) {
          $('status').textContent = 'LIVE';
          $('status').className = 'status';
          $('errbox').style.display = 'none';
        } else {
          $('status').textContent = 'EROARE';
          $('status').className = 'status err';
          $('errbox').style.display = 'block';
          $('errbox').textContent = data.error || 'Eroare necunoscuta';
        }
      } catch (err) {
        $('status').textContent = 'EROARE';
        $('status').className = 'status err';
        $('errbox').style.display = 'block';
        $('errbox').textContent = 'Nu pot citi /api/data: ' + err;
      }
    }

    refresh();
    setInterval(refresh, 5000);
  </script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8765"))
    app.run(host="0.0.0.0", port=port, debug=False)
