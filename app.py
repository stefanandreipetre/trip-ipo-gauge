"""
TRIP IPO Gauge - Server Flask pentru Render.com
"""
import re
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, send_from_directory

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    import os
    os.system("pip install requests beautifulsoup4 --quiet")
    import requests
    from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='static')

RETAIL_TOTAL = 41_750_000
REFRESH_SEC  = 5
BVB_URL      = "https://www.bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx?s=TRIP"

state = {"subscribed": 0, "timestamp": "—", "error": None}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
    "Referer": "https://www.bvb.ro/",
})

def fetch_bid_vol():
    try:
        r = SESSION.get(BVB_URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator="|")
        match = re.search(r"Bid\s*/\s*Ask\s*Vol\.?\s*\|?\s*([\d\.]+)\s*/", text, re.IGNORECASE)
        if match:
            raw = match.group(1).replace(".", "").replace(",", "")
            return int(raw), None
        for td in soup.find_all("td"):
            if "Bid" in td.get_text() and "Vol" in td.get_text():
                sib = td.find_next_sibling("td")
                if sib:
                    nums = re.findall(r"[\d\.]+", sib.get_text(strip=True))
                    if nums:
                        return int(nums[0].replace(".", "")), None
        return None, "Nu s-a gasit Bid Vol in pagina BVB"
    except Exception as e:
        return None, str(e)

def refresh_loop():
    while True:
        val, err = fetch_bid_vol()
        state["timestamp"] = datetime.now().strftime("%H:%M:%S")
        if val is not None:
            state["subscribed"] = val
            state["error"] = None
            pct = round(val / RETAIL_TOTAL * 100, 1)
            print(f"[{state['timestamp']}] Bid Vol: {val:,} -> {pct}%")
        else:
            state["error"] = err
            print(f"[{state['timestamp']}] Eroare: {err}")
        time.sleep(REFRESH_SEC)

# Porneste thread fetch in background
t = threading.Thread(target=refresh_loop, daemon=True)
t.start()

@app.route("/data")
def data():
    return jsonify(state)

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "TRIP IPO Gauge",
        "short_name": "TRIP IPO",
        "description": "Christian Tour IPO - Subscrieri Retail Live",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#f1f5f9",
        "theme_color": "#00AEEF",
        "orientation": "portrait",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.route("/sw.js")
def service_worker():
    sw = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => clients.claim());
self.addEventListener('fetch', e => {
  if (e.request.url.includes('/data')) return;
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
"""
    from flask import Response
    return Response(sw, mimetype='application/javascript')

@app.route("/logo.png")
def logo():
    return send_from_directory('static', 'logo.png')

@app.route("/icon-192.png")
def icon192():
    return send_from_directory('static', 'icon-192.png')

@app.route("/icon-512.png")
def icon512():
    return send_from_directory('static', 'icon-512.png')

@app.route("/")
def index():
    return send_from_directory('static', 'index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=False)
