# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file Flask web app that displays a live "gauge" of subscriptions to the TRIP (Romanian) IPO. The web service is a passive relay: it does not scrape the IPO data itself. A separate **PC-side scraper** (not in this repo) pushes snapshots to `POST /push`; browsers poll `GET /api/data` to render the gauge.

```
[PC scraper] --POST /push (X-Push-Secret)--> [Flask app on Render] <--GET /api/data-- [Browser PWA]
```

If `/api/data` returns stale data (`age_seconds` large) or `ok: false` with `"Astept date de la PC..."`, the issue is upstream (PC scraper isn't pushing) — not in this codebase.

## Commands

```bash
pip install -r requirements.txt

# Local dev server (defaults to port 8765; override with PORT)
python app.py

# Production-equivalent (matches Procfile)
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 30
```

No test suite, linter, or build step exists.

### Useful manual checks

```bash
# Simulate a push from the PC scraper
curl -X POST http://localhost:8765/push \
  -H "X-Push-Secret: trip2026" \
  -H "Content-Type: application/json" \
  -d '{"subscribed": 1234567, "snapshots": [{"time":"10:00:00","subscribed":1234567,"percentage":2.96}]}'

curl http://localhost:8765/api/data
curl http://localhost:8765/health
curl -OJ http://localhost:8765/api/snapshots/csv
```

## Architecture notes that aren't obvious from a single file

- **Frontend is a real file:** `index.html` sits next to `app.py`, is read once at module import into `_HTML`, and served on every `/` request. Just edit `index.html` directly. (Historical note: it used to be a base64 blob inside `app.py`; the old loose `logo.png` was actually an earlier HTML version, since removed.)

- **Server state is in-process, in-memory only.** `_state`, `_cache`, and `_last_push` are module globals. Restarting the dyno wipes all snapshot history; there is no database. Single-worker config (`--workers 1` in the Procfile) is deliberate — multiple workers would have divergent state because pushes only hit one of them.

- **`RETAIL_TOTAL` is the denominator** for the displayed percentage (default 41,750,000). The PC scraper sends raw `subscribed` counts; the server computes `percentage` and `available` itself. If the IPO size changes, set `RETAIL_TOTAL` rather than changing the scraper.

- **CSV snapshot conversion uses hardcoded constants**: `ron = subscribed * 2.135` (issue price) and `eur = ron / 5.2488` (FX rate). Both are baked into `snapshots_csv()` in `app.py`. Update them if the IPO terms or FX assumption change.

- **Auth is one shared secret** (`PUSH_SECRET`, default `"trip2026"` — clearly a dev-only fallback). It guards `/push` via the `X-Push-Secret` header. The default must be overridden in production; the PC scraper must be configured with the matching value.

- **`/api/data` and `/data` are aliases**, and there's a small `CACHE_SEC`-second response cache (default 3s) that is invalidated immediately on every successful push, so browsers see new data the moment it arrives even with caching on.

- **PWA icons** are served by explicit `/icon-192.png` and `/icon-512.png` routes (`send_from_directory`) — the actual PNGs sit next to `app.py`. There is no `static/` folder; any other static asset would need its own route the same way.

## Deployment

`Procfile` targets a Heroku-style platform (Render, per the comments in `app.py`). Required env vars in production: `PUSH_SECRET`, `RETAIL_TOTAL`, `PORT` (platform-provided), optionally `CACHE_SECONDS`.
