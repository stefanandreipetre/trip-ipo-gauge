"""
TRIP Gauge pentru Render.

Render serveste pagina publica si face fetch server-side catre computerul de acasa.
Setare necesara in Render:
HOME_SERVER_URL = http://petre.go.ro:8765
optional:
HOME_SERVER_TOKEN = secretul tau
"""

import os
import time
from urllib.parse import urljoin

import requests
from flask import Flask, Response, jsonify

app = Flask(__name__)

RETAIL_TOTAL = int(os.getenv("RETAIL_TOTAL", "41750000"))
TOTAL_OFFER = int(os.getenv("TOTAL_OFFER", "83500000"))
SUBSCRIPTION_PRICE = os.getenv("SUBSCRIPTION_PRICE", "2,135 lei")
HOME_SERVER_URL = os.getenv("HOME_SERVER_URL", "").strip().rstrip("/")
HOME_SERVER_TOKEN = os.getenv("HOME_SERVER_TOKEN", "").strip()
FETCH_TIMEOUT = float(os.getenv("FETCH_TIMEOUT", "8"))
CACHE_SECONDS = float(os.getenv("CACHE_SECONDS", "3"))

_session = requests.Session()
_cache = {"at": 0.0, "payload": None}


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
            "timestamp": "--",
            "source": "render",
            "retail_total": RETAIL_TOTAL,
            "total_offer": TOTAL_OFFER,
            "subscription_price": SUBSCRIPTION_PRICE,
            "error": "Lipseste HOME_SERVER_URL in Render Environment.",
        }

    headers = {"Accept": "application/json", "User-Agent": "TRIP-Gauge-Render/2.0"}
    if HOME_SERVER_TOKEN:
        headers["X-API-Key"] = HOME_SERVER_TOKEN
        headers["X-TRIP-Token"] = HOME_SERVER_TOKEN

    try:
        r = _session.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        subscribed = int(data.get("subscribed") or data.get("bid_vol") or 0)
        percentage = round((subscribed / RETAIL_TOTAL) * 100, 2) if RETAIL_TOTAL else 0
        available = max(RETAIL_TOTAL - subscribed, 0)

        return {
            "ok": bool(data.get("ok", True)),
            "subscribed": subscribed,
            "available": available,
            "percentage": percentage,
            "timestamp": data.get("timestamp") or data.get("updated_at") or "--",
            "source": "home_server",
            "home_source": data.get("source", "home"),
            "retail_total": RETAIL_TOTAL,
            "total_offer": TOTAL_OFFER,
            "subscription_price": SUBSCRIPTION_PRICE,
            "error": data.get("error"),
        }
    except Exception as exc:
        last = _cache.get("payload")
        if last:
            fallback = dict(last)
            fallback["ok"] = False
            fallback["source"] = "render_cache"
            fallback["error"] = f"Nu pot citi serverul de acasa: {exc}"
            return fallback

        return {
            "ok": False,
            "subscribed": 0,
            "available": RETAIL_TOTAL,
            "percentage": 0,
            "timestamp": "--",
            "source": "render",
            "retail_total": RETAIL_TOTAL,
            "total_offer": TOTAL_OFFER,
            "subscription_price": SUBSCRIPTION_PRICE,
            "error": f"Nu pot citi serverul de acasa: {exc}",
        }


@app.get("/health")
def health():
    return jsonify({"ok": True, "home_server_configured": bool(HOME_SERVER_URL), "home_data_url": _home_data_url() or None})


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


INDEX_HTML = r'''<!doctype html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TRIP · Christian '76 Tour SA</title>
  <style>
    :root{
      --ink:#162744; --muted:#7c8aa7; --line:#dce5ef; --panel:#f8fbff;
      --blue:#05aef2; --green:#35d09a; --orange:#ff711d; --track:#e7edf4;
    }
    *{box-sizing:border-box}
    body{margin:0;min-height:100vh;background:linear-gradient(135deg,#eef8fb 0%,#fff7f0 100%);display:grid;place-items:start center;padding:0;font-family:Georgia,'Times New Roman',serif;color:var(--ink)}
    .shell{width:100%;max-width:650px;background:white;border-radius:0 22px 22px 22px;border:1px solid var(--line);box-shadow:0 16px 40px rgba(31,49,75,.10);overflow:hidden}
    .top{height:103px;background:linear-gradient(90deg,#fbfdff,#fff8f2);display:grid;grid-template-columns:104px 1fr 132px;align-items:center;border-bottom:1px solid var(--line);padding:0 28px 0 30px;gap:14px}
    .logo{width:62px;height:62px;border-radius:8px;display:grid;place-items:center;justify-self:center;position:relative;color:#f15b22;font-weight:700;font-size:9px;text-align:center;line-height:1.05}
    .logo:before{content:'';width:36px;height:36px;background:#ff5b1a;border-radius:5px;display:block;position:absolute;top:4px;left:13px}
    .logo:after{content:'Christian Tour';position:absolute;bottom:5px;left:0;right:0;color:#173468;font-size:8px;font-family:Arial,sans-serif;font-weight:700}
    .mark{position:absolute;top:13px;left:24px;width:20px;height:16px;border-radius:50%;border:6px solid #fff;border-right-color:transparent;border-bottom-color:transparent;transform:rotate(-22deg);z-index:2}
    .kicker{display:flex;align-items:center;gap:12px;font-size:17px;letter-spacing:2px;color:#344564}
    .badge{background:#0bb8ed;color:white;border-radius:6px;padding:4px 10px;font-family:'Courier New',monospace;font-weight:800;font-size:16px;letter-spacing:3px}
    h1{margin:4px 0 0;font-size:23px;line-height:1.1;letter-spacing:.2px}
    .subtitle{color:#8a94ad;font-size:14px;margin-top:4px}
    .live{text-align:right;align-self:start;padding-top:30px;color:#7d89a7;font-family:'Courier New',monospace;font-size:13px}
    .pill{display:inline-flex;align-items:center;gap:8px;border:1px solid #a8ebc8;background:#eafff3;color:#04894c;border-radius:999px;padding:4px 13px;font-family:'Courier New',monospace;font-size:13px;margin-bottom:4px}
    .dot{width:9px;height:9px;border-radius:50%;background:#23bf70;display:inline-block}
    .tabs{height:49px;display:grid;grid-template-columns:1fr 1fr;border-bottom:1px solid var(--line);font-size:16px;letter-spacing:2px;color:#7c8aa7}
    .tab{display:grid;place-items:center;border-right:1px solid var(--line)}
    .tab.active{background:#eefbff;color:#008fe6;border-bottom:2px solid var(--blue)}
    .content{padding:70px 30px 0}
    .gauge-wrap{height:220px;position:relative;display:grid;place-items:start center}
    svg.gauge{width:345px;height:210px;overflow:visible}
    .tick{font-family:Georgia,'Times New Roman',serif;font-size:12px;fill:#8290aa}
    .needle{transition:transform .5s ease;transform-origin:170px 170px}
    .center{position:absolute;top:116px;left:0;right:0;text-align:center;pointer-events:none}
    .pct{font-family:Arial,sans-serif;color:var(--green);font-weight:800;font-size:34px;letter-spacing:.5px}
    .pct small{font-size:20px}.center .caption{color:#7d88a3;font-size:13px;margin-top:-2px}
    .cards{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:-4px}
    .box{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:12px 16px;min-height:80px}
    .box .name{font-size:14px;color:#455778}.box .big{font-family:'Courier New',monospace;font-size:19px;font-weight:800;margin-top:4px;color:var(--blue)}
    .box .big.green{color:var(--green)}.box .big.purple{color:#9b91ff}.box .small{font-size:11px;color:#8996b2;margin-top:1px}
    .progress-head{display:flex;justify-content:space-between;color:#7d88a5;font-size:13px;margin:17px 0 6px}.progress{height:11px;border-radius:999px;background:var(--track);overflow:hidden}.progress-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--blue),var(--orange));border-radius:999px;transition:width .5s ease}
    .snap{border-top:1px solid var(--line);margin-top:18px;padding:12px 0 15px}.snap-title{font-size:14px;color:#8b97b1;text-transform:uppercase}.snap-line{font-family:'Courier New',monospace;color:#008df1;font-size:12px;margin-top:6px;display:grid;grid-template-columns:150px 1fr;gap:12px}
    .foot{height:38px;border-top:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 30px;color:#8b97b1;font-size:12px;background:#fbfdff}
    .error{display:none;margin:12px 30px 0;border:1px solid #ffd0d0;background:#fff5f5;color:#b32626;border-radius:10px;padding:9px 11px;font-family:Arial,sans-serif;font-size:12px}
    @media(max-width:560px){body{padding:0}.shell{border-radius:0;max-width:none}.top{grid-template-columns:76px 1fr 96px;padding:0 14px;gap:8px}.kicker{font-size:14px}.badge{font-size:13px}h1{font-size:19px}.content{padding:54px 18px 0}.cards{gap:10px}.box{padding:10px}.snap-line{grid-template-columns:120px 1fr}.foot{padding:0 18px}}
  </style>
</head>
<body>
  <main class="shell">
    <header class="top">
      <div class="logo"><span class="mark"></span></div>
      <div>
        <div class="kicker"><span class="badge">TRIP</span><span>BVB · IPO 2026</span></div>
        <h1>Christian '76 Tour SA</h1>
        <div class="subtitle">Subscrieri Retail · 21--28 mai 2026</div>
      </div>
      <div class="live"><div id="status" class="pill"><span class="dot"></span>Live BVB</div><div id="clock">--:--:--</div></div>
    </header>
    <nav class="tabs"><div class="tab active">📊 GAUGE</div><div class="tab">ℹ️ PROSPECT</div></nav>
    <div id="error" class="error"></div>
    <section class="content">
      <div class="gauge-wrap">
        <svg class="gauge" viewBox="0 0 340 220" aria-label="Gauge TRIP">
          <path d="M 55 170 A 135 135 0 0 1 285 170" fill="none" stroke="#e7edf4" stroke-width="22" stroke-linecap="round"/>
          <path id="arc" d="M 55 170 A 135 135 0 0 1 285 170" fill="none" stroke="#35d09a" stroke-width="22" stroke-linecap="round" stroke-dasharray="0 999"/>
          <text x="25" y="148" class="tick">0%</text><text x="220" y="112" class="tick">25%</text><text x="312" y="183" class="tick">50%</text>
          <g id="needle" class="needle"><line x1="170" y1="170" x2="276" y2="44" stroke="#ff711d" stroke-width="5" stroke-linecap="round"/><circle cx="170" cy="170" r="10" fill="#ff711d"/><circle cx="170" cy="170" r="4" fill="white"/></g>
        </svg>
        <div class="center"><div id="pct" class="pct">--<small>%</small></div><div class="caption">din transa retail</div></div>
      </div>
      <div class="cards">
        <div class="box"><div class="name">Subscrise (Bid Vol.)</div><div id="subscribed" class="big green">--</div><div id="subscribedRon" class="small">-- RON</div></div>
        <div class="box"><div class="name">Disponibile</div><div id="available" class="big">--</div><div class="small">ramase</div></div>
        <div class="box"><div class="name">Transa retail</div><div id="retail" class="big">--</div><div class="small">actiuni (50% din oferta)</div></div>
        <div class="box"><div class="name">Pret subscriere</div><div id="price" class="big purple">--</div><div class="small">fix retail · -5% early bird</div></div>
      </div>
      <div class="progress-head"><span>0%</span><span>Transa completa: <span id="retail2">--</span> actiuni</span></div>
      <div class="progress"><div id="bar" class="progress-fill"></div></div>
      <div class="snap"><div class="snap-title">Snapshots confirmate (sursa: Bursa.ro)</div><div class="snap-line"><span>21 mai ~13:30</span><span>5.60M (13.4%) -- dupa 3.5h de la deschidere</span></div><div class="snap-line"><span>22 mai EOD est.</span><span>8.35M (20.0%) -- ~o cincime din transa retail</span></div></div>
    </section>
    <footer class="foot"><span>Date live BVB · refresh 5s · Bid Vol = subscrieri retail acumulate</span><span>Christian '76 Tour SA</span></footer>
  </main>
  <script>
    const $=id=>document.getElementById(id);
    const nf=new Intl.NumberFormat('en-US',{maximumFractionDigits:2});
    const intf=new Intl.NumberFormat('en-US');
    const priceNumber=2.135;
    function compact(n){n=Number(n||0); if(n>=1000000) return nf.format(n/1000000)+'M'; if(n>=1000) return nf.format(n/1000)+'K'; return intf.format(n)}
    function setClock(){ $('clock').textContent=new Date().toLocaleTimeString('ro-RO',{hour:'2-digit',minute:'2-digit',second:'2-digit'}); }
    function gauge(percent){
      const p=Math.max(0,Math.min(50,Number(percent)||0));
      const ratio=p/50;
      const arcLen=424;
      $('arc').setAttribute('stroke-dasharray',(arcLen*ratio)+' '+arcLen);
      const angle=-90 + 180*ratio;
      $('needle').style.transform='rotate('+angle+'deg)';
      $('bar').style.width=Math.max(0,Math.min(100,Number(percent)||0))+'%';
    }
    async function refresh(){
      try{
        const r=await fetch('/api/data?ts='+Date.now(),{cache:'no-store'});
        const d=await r.json();
        const subscribed=Number(d.subscribed||0), total=Number(d.retail_total||41750000), available=Number(d.available ?? Math.max(total-subscribed,0));
        const pct=Number(d.percentage||0);
        $('pct').innerHTML=pct.toFixed(1)+'<small>%</small>';
        $('subscribed').textContent=compact(subscribed);
        $('subscribedRon').textContent=intf.format(Math.round(subscribed*priceNumber))+' RON';
        $('available').textContent=compact(available);
        $('retail').textContent=compact(total);
        $('retail2').textContent=compact(total);
        $('price').textContent=d.subscription_price||'2,135 lei';
        gauge(pct);
        if(d.ok && !d.error){$('status').innerHTML='<span class="dot"></span>Live BVB';$('error').style.display='none'}
        else{$('status').innerHTML='<span class="dot"></span>Date cache';$('error').style.display='block';$('error').textContent=d.error||'Eroare necunoscuta'}
      }catch(e){$('status').innerHTML='<span class="dot"></span>Eroare';$('error').style.display='block';$('error').textContent='Nu pot citi /api/data: '+e}
    }
    setClock(); setInterval(setClock,1000); refresh(); setInterval(refresh,5000);
  </script>
</body>
</html>'''


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8765"))
    app.run(host="0.0.0.0", port=port, debug=False)
