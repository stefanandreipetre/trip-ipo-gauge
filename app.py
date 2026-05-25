import os, time, json, re
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, Response, request, abort, send_from_directory

app          = Flask(__name__)
BUCHAREST    = ZoneInfo("Europe/Bucharest")
RETAIL_TOTAL = int(os.getenv("RETAIL_TOTAL", "41750000"))
PUSH_SECRET  = os.getenv("PUSH_SECRET", "trip2026")
CACHE_SEC    = float(os.getenv("CACHE_SECONDS", "3"))

# Stare — actualizata de PC prin POST /push
_state = {
    "ok":         False,
    "subscribed": 0,
    "percentage": 0.0,
    "timestamp":  "—",
    "error":      "Astept date de la PC...",
    "snapshots":  [],   # lista completa trimisa de PC
}
_cache       = {"at": 0.0, "payload": None}
_last_push   = 0.0


def _now_buc():
    return datetime.now(BUCHAREST).strftime("%H:%M:%S")


# ── /push  (PC → Render) ──────────────────────────────────────────────────────
@app.route("/push", methods=["POST"])
def push():
    global _last_push
    secret = request.headers.get("X-Push-Secret", "")
    if secret != PUSH_SECRET:
        abort(403)
    d = request.get_json(force=True) or {}
    sub     = int(d.get("subscribed", 0))
    pct     = round(sub / RETAIL_TOTAL * 100, 4) if RETAIL_TOTAL else 0
    _state.update({
        "ok":         bool(d.get("ok", sub > 0)),
        "subscribed": sub,
        "percentage": pct,
        "timestamp":  d.get("timestamp") or _now_buc(),
        "error":      d.get("error"),
        "available":  max(RETAIL_TOTAL - sub, 0),
        "snapshots":  d.get("snapshots", []),   # istoricul complet de la PC
    })
    _last_push = time.time()
    _cache["payload"] = None   # invalideaza cache-ul
    return jsonify({"ok": True, "subscribed": sub, "snapshots": len(_state["snapshots"])})


# ── /api/data  (browser → Render) ────────────────────────────────────────────
@app.route("/api/data")
@app.route("/data")
def data():
    now = time.time()
    if _cache["payload"] and now - _cache["at"] < CACHE_SEC:
        return jsonify(_cache["payload"])
    age = round(now - _last_push) if _last_push else 9999
    payload = dict(_state)
    payload["age_seconds"] = age
    _cache["payload"] = payload
    _cache["at"]      = now
    return jsonify(payload)


# ── /api/snapshots/csv  (download) ───────────────────────────────────────────
@app.route("/api/snapshots/csv")
def snapshots_csv():
    snaps = _state.get("snapshots", [])
    lines = ["ora,actiuni_subscrise,procent,ron,eur"]
    for s in snaps:
        sub  = int(s.get("subscribed", 0))
        pct  = float(s.get("percentage", 0))
        ron  = round(sub * 2.135)
        eur  = round(ron / 5.2488)
        lines.append(f"{s.get('time','')},{sub},{pct},{ron},{eur}")
    csv_data = "\n".join(lines)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=trip_ipo_snapshots.csv"}
    )


# ── /health ───────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({
        "ok":              True,
        "push_secret_set": bool(PUSH_SECRET),
        "last_push_ago_s": round(time.time() - _last_push) if _last_push else None,
        "snapshots":       len(_state.get("snapshots", [])),
    })


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name":"TRIP IPO Gauge","short_name":"TRIP IPO",
        "start_url":"/","display":"standalone",
        "background_color":"#ffffff","theme_color":"#06275c",
        "icons":[
            {"src":"/icon-192.png","sizes":"192x192","type":"image/png"},
            {"src":"/icon-512.png","sizes":"512x512","type":"image/png"}
        ]
    })

@app.route("/sw.js")
def sw():
    return Response(
        "self.addEventListener('fetch',e=>e.respondWith(fetch(e.request)));",
        mimetype="application/javascript")

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "index.html"), "rb") as _f:
    _HTML = _f.read()

@app.route("/")
def index():
    return Response(_HTML, mimetype="text/html; charset=utf-8")

@app.route("/icon-192.png")
def icon_192():
    return send_from_directory(_HERE, "icon-192.png", mimetype="image/png")

@app.route("/icon-512.png")
def icon_512():
    return send_from_directory(_HERE, "icon-512.png", mimetype="image/png")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8765"))
    app.run(host="0.0.0.0", port=port, debug=False)
