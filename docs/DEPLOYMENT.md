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

## Configuration

All configuration is currently hardcoded in `src/main.py`. Key values to change for deployment:

| Setting | Location | Default | Notes |
|---------|----------|---------|-------|
| `debug` | `app.run(debug=True)` | `True` | Set to `False` in production |
| `host` | `app.run(host='0.0.0.0')` | `0.0.0.0` | Binds to all interfaces |
| `port` | `app.run(port=5000)` | `5000` | |
| `RATE_LIMIT_SECONDS` | `src/routes/api.py` | `5` | Seconds between requests per IP |
| `saved_slides/` path | `src/utils/slide_storage.py` | `src/saved_slides/` | Local disk; swap for remote storage in production |

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

> **Note**: The current in-memory rate limiter does not work correctly with multiple Gunicorn workers (each worker has its own state). Replace it with `Flask-Limiter` + Redis before scaling.

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
Replace the in-memory rate limiter in `api.py` with `Flask-Limiter`:

```bash
uv add flask-limiter[redis]
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, storage_uri="redis://localhost:6379")

@api_bp.route('/search')
@limiter.limit("10 per minute")
def search_song():
    ...
```

### Slide Storage at Scale
The current file-based storage (`src/saved_slides/`) is not suitable for multi-user deployments. To support multiple users:

1. Replace `src/utils/slide_storage.py` with a database-backed implementation (e.g. SQLite, PostgreSQL).
2. Store `.pptx` files in object storage (e.g. AWS S3, Google Cloud Storage) keyed by UUID.
3. Add session/user scoping so each user only sees their own slides.

---

## Docker (Optional)

A minimal `Dockerfile` for containerised deployment:

```dockerfile
FROM python:3.10-slim

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
docker run -p 5000:5000 -v $(pwd)/src/saved_slides:/app/src/saved_slides band-deck
```

Mount `src/saved_slides/` as a volume to persist saved slides across container restarts.

---

## Verifying the Deployment

After starting, run:

```bash
# Health check — should return 404 (no root route defined) or a redirect
curl -I http://localhost:5000/

# API smoke test
curl "http://localhost:5000/api/saved_slides"
# Expected: []  (or a list if slides are already saved)
```
