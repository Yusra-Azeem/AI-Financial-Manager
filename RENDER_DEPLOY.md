# Deploying to Render (no Docker)

`render.yaml` (repo root) is a Blueprint — Render reads it and creates all
three resources (backend, frontend, Postgres) in one go, using Render's
native Python and static-site runtimes — no Dockerfile involved.

## 1. Push this repo structure to GitHub

Render Blueprints need `render.yaml` at the repo root, with `backend/` and
`frontend/` as the `rootDir`s referenced inside it. If your actual repo
layout differs, adjust `rootDir` in `render.yaml` to match.

## 2. Merge the extra Python dependencies

`backend/agent/requirements-additions.txt` lists what the agent/deployment
layer needs (langgraph, the postgres checkpoint backend, gunicorn) on top
of whatever Roshni's `requirements.txt` already has. The Blueprint's
`buildCommand` installs both files separately so you don't have to merge
them by hand:

```
pip install -r requirements.txt -r agent/requirements-additions.txt
```

If you'd rather have one file, just copy the contents of
`requirements-additions.txt` into `requirements.txt` and simplify
`buildCommand` to `pip install -r requirements.txt`.

## 3. Deploy the Blueprint

Render dashboard → **New +** → **Blueprint** → connect the repo → Render
detects `render.yaml` and shows you the 3 resources it's about to create →
**Apply**.

## 4. Set the secret env vars

`render.yaml` marks these `sync: false`, meaning Render won't set them for
you — go to the backend service → **Environment** and add:

- `GEMINI_API_KEY` or `OPENAI_API_KEY` (whichever `LLM_PROVIDER` you use)
- Anything else `config.py` requires from `.env.example` that isn't already
  wired up (check `backend/.env.example` against the Blueprint's `envVars`)

If you're using an existing **Supabase** Postgres instead of Render's
managed one: delete the `databases:` block from `render.yaml`, and instead
add `DATABASE_URL` as a secret env var on the backend service with your
Supabase connection string.

## 5. Seed the database

Render's native Python services support one-off **Jobs** using the same
build as your web service. Dashboard → backend service → **Jobs** → run:

```
python seed_data.py
```

against the same `DATABASE_URL`. Run this once after the first deploy.

## 6. Fix up the frontend URL

The Blueprint guesses the backend's URL will be
`https://fin-rm-backend.onrender.com`. Render usually honors the `name:`
you set, but double-check the backend service's actual URL after first
deploy and update `VITE_API_BASE_URL` on the frontend service if it
differs — then trigger a manual redeploy of the frontend (env vars are
baked in at Vite build time, so changing them requires a rebuild, not just
a restart).

## 7. CORS

Add this to `main.py` (backend) if it isn't already there, so the deployed
frontend origin is allowed:

```python
from fastapi.middleware.cors import CORSMiddleware
import os

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 8. Health check

`render.yaml` points Render's health check at `/docs` (FastAPI's built-in
Swagger UI, always 200 if the app boots) since there's no dedicated
`/health` route yet. Feel free to add one to `main.py`:

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```
and update `healthCheckPath: /health` in `render.yaml`.

## Notes

- **Port binding**: Render injects a `$PORT` env var and expects your app
  to bind to it — the Blueprint's `startCommand` already does this
  (`-b 0.0.0.0:$PORT`), so no changes needed unless you customize it further.
- **Free/starter plan**: services spin down after inactivity — the first
  request after idle can take ~30-50s while it wakes up (LangGraph + LLM
  calls will feel slow on that first hit only).
- **Scaling past 1 instance**: `CHECKPOINT_BACKEND=postgres` is required —
  sqlite/memory checkpointers won't share negotiation sessions across
  instances.
