# 🚀 Deployment Guide

## Local Development (Default)

```bash
# Install dependencies
uv sync

# Start the dev server (auto-reload enabled by default in main.py)
uv run python src/main.py
```

The server starts at **http://localhost:5000** in debug mode (auto-reload on file changes).

---

## Requirements: Node.js & Marp CLI

The HTML/Marp pipeline (preview, save, regenerate, compile) shells out to
the [`marp` CLI](https://github.com/marp-team/marp-cli). The CLI is a
Node.js application, so Node.js must be available on the host.

| Component | Minimum version | Notes |
| :-------- | :------------- | :---- |
| Node.js   | 16.0.0         | Required by Marp CLI 3.x. Use `nvm install 16` if your distro ships older Node. |
| Marp CLI  | 3.0.0          | Installed via `npm install -g @marp-team/marp-cli` |

### Install on Linux / macOS

```bash
# 1. Install Node.js (skip if your distro ships >=16 already)
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs

# 2. Install Marp CLI globally
npm install -g @marp-team/marp-cli

# 3. Verify
marp --version
# > @marp-team/marp-cli v3.x.x
```

### Install on Windows (PowerShell)

```powershell
choco install nodejs-lts
npm install -g @marp-team/marp-cli
marp --version
```

### Verifying from the API

Once the server is running, hit the health endpoint to confirm the CLI is
discoverable from the Python process:

```bash
curl http://localhost:5000/api/health
# {
#   "status": "ok",
#   "marp_cli": {"available": true, "note": "Marp CLI is available."},
#   "storage": {"path": "...", "files": N, "bytes": N}
# }
```

`status` is `ok` only when Marp is installed; otherwise it's `degraded`
and the `note` explains what is missing.

---

## Configuration

All configuration is currently hardcoded in `src/main.py`. Key values to change for deployment:

| Setting | Location | Default | Notes |
|---------|----------|---------|-------|
| `debug` | `app.run(debug=True)` | `True` | Set to `False` in production |
| `host` | `app.run(host='0.0.0.0')` | `0.0.0.0` | Binds to all interfaces |
| `port` | `app.run(port=5000)` | `5000` | |
| `saved_slides/` path | `src/utils/slide_storage.py` | `data/saved_slides/` | Local disk; swap for remote storage in production |

To disable debug mode:
```python
# src/main.py
app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## Environment Variables

Band-Deck does not currently use environment variables. If you need to externalize config, add a `.env` file and load it with `python-dotenv` (not currently a dependency).

---

## Production Deployment Notes

> ⚠️ **Band-Deck is designed for personal/small-team use.** The following notes apply if you choose to deploy it more broadly.

### WSGI Server
Flask's built-in server is not suitable for production. Use a WSGI server instead:

```bash
# Install gunicorn (add to pyproject.toml first)
uv add gunicorn

# Run with 2 workers
uv run gunicorn -w 2 -b 0.0.0.0:5000 'src.main:app'
```

> **Note**: Rate limiting is currently disabled. Add a shared limiter, such as `Flask-Limiter` backed by Redis, before scaling a public deployment.

### Reverse Proxy (nginx)
Put nginx in front of Gunicorn to handle TLS, static file serving, and request buffering:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/band-deck/src/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Rate Limiting at Scale
Add `Flask-Limiter` with shared Redis storage:

```bash
uv add flask-limiter[redis]
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, storage_uri="redis://localhost:6379")

@api_bp.route('/search', methods=['GET'])
@limiter.limit("10 per minute")
def search_song():
    ...
```

### Slide Storage at Scale
The current file-based storage (`data/saved_slides/`) is not suitable for multi-user deployments. To support multiple users:

1. Replace `src/utils/slide_storage.py` with a database-backed implementation (e.g. SQLite, PostgreSQL).
2. Store the multi-format artefacts (`*.yaml`, `*.marp.md`, `*.html`, `*.json`, optional `*.pdf`) in object storage (e.g. AWS S3, Google Cloud Storage) keyed by UUID. PowerPoint export has been retired.
3. Add session/user scoping so each user only sees their own slides.

---

## Docker (Optional)

A minimal `Dockerfile` for containerised deployment. Note that `apt-get` packages are added before `uv sync` so that `/api/health` reports `marp_cli.available: true` from the first request:

```dockerfile
FROM python:3.10-slim

# Install Node.js and the Marp CLI (required by src/utils/html_renderer.py
# and src/utils/marp_generator.py at request time).
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @marp-team/marp-cli && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app
COPY . .

# Install dependencies (no dev extras)
RUN uv sync --no-dev

EXPOSE 5000

CMD ["uv", "run", "python", "src/main.py"]
```

Build and run:
```bash
docker build -t band-deck .
docker run -p 5000:5000 -v $(pwd)/data/saved_slides:/app/data/saved_slides band-deck
```

Mount `data/saved_slides/` as a volume to persist saved slides across container restarts.

---

## Verifying the Deployment

After starting, run:

```bash
# Health check — should return 404 (no root route defined) or a redirect
curl -I http://localhost:5000/

# API smoke test
curl "http://localhost:5000/api/saved_slides"
# Expected: []  (or a list if slides are already saved)

# Operational probe
curl "http://localhost:5000/api/health"
# Reports Marp CLI availability and recorded storage bytes.
```

---

## Subprocess Timeouts & Resource Limits

`src/utils/html_renderer.py` shells out to the `marp` CLI. The defaults
are tuned for typical worship songs but **must** be reviewed before
production:

| Setting                  | Default | Where to change                                  |
| :----------------------- | :------ | :----------------------------------------------- |
| `DEFAULT_RENDER_TIMEOUT_SECONDS` | 30s  | `src/utils/html_renderer.py`              |
| `DEFAULT_HEALTHCHECK_TIMEOUT_SECONDS` | 5s | `src/utils/html_renderer.py`             |
| `MAX_MARKDOWN_BYTES`     | 2 MiB   | `src/utils/html_renderer.py`                    |

Increase the render timeout only if you ship particularly large song
maps; the subprocess should never run unbounded, so do not raise above
~120 seconds.

For production traffic, also consider:
- Wrapping the Flask app with `gunicorn` (or another WSGI server)
  and configuring `--timeout 120` so a stuck Marp subprocess doesn't
  pin a worker for longer than the render timeout.
- Setting a higher process limit (e.g. `ulimit -n 4096`) if you run
  many concurrent renders; each `marp` subprocess is short-lived but
  can momentarily spike the open-file count.

---

## Storage Directory Permissions

The slide library directory is defined by the `SLIDES_DIR` constant in `src/utils/slide_storage.py`. On a fresh host, ensure the resolved directory is **writable by the runtime user**:

```bash
mkdir -p data/saved_slides
chmod 0750 data/saved_slides        # rwx for owner, rx for group
chown -R band-deck:band-deck data/saved_slides
```

When running in Docker, mount the directory as a writable volume:

```bash
docker run -p 5000:5000 \
  -v $(pwd)/data/saved_slides:/app/data/saved_slides \
  band-deck:latest
```

In nginx+Gunicorn productions, point `user app;` to the same UID that
owns the directory.

---

## Production Deployment Checklist

- [ ] Python 3.10+ installed (via `uv python install 3.10`)
- [ ] `uv sync --no-dev` succeeds
- [ ] Node.js >= 16.0.0 (`node --version`)
- [ ] `@marp-team/marp-cli` installed globally (`marp --version`)
- [ ] `data/saved_slides/` writable by the runtime user
- [ ] `/api/health` reports `status: ok` and `marp_cli.available: true`
- [ ] Behind a reverse proxy (nginx/Caddy) with TLS
- [ ] WSGI server with timeout >= `DEFAULT_RENDER_TIMEOUT_SECONDS + 30`
- [ ] Logging routed somewhere durable (stderr is fine; `LOG_FILE` env var still optional)
- [ ] The end-to-end smoke test below passes

### Smoke test

```bash
# Render one slide end-to-end (uses Marp CLI)
curl -sS -X POST http://localhost:5000/api/preview \
  -H 'Content-Type: application/json' \
  -d '{"song": {"title":"Smoke Test","authors":["Test"],"target_key":"C","sections":{"V1":{"name":"V1","type":"verse","lines":[{"text":"Hello world","chords":[]}]}},"arrangement":["V1"]}}' \
  | jq '.html_content | length'
# Expected: > 1000 (real HTML output)
```
