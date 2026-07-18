# syntax=docker/dockerfile:1
# Self-contained image: builds the SPA, then runs the stdlib server with the
# game data baked in. Build it where data/ exists (your machine) — data/raw and
# the built SPA are gitignored, so a from-git build on the host would miss them.
# See docs/deploy.md.

# --- stage 1: build the single-page app ----------------------------------
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json ./
RUN npm install
COPY web/ ./
# vite's base is /app/; force a self-contained output dir (its configured
# outDir points outside this stage)
RUN npx vite build --outDir dist --emptyOutDir

# --- stage 2: runtime ----------------------------------------------------
FROM python:3.11-slim
# links the GHCR package to the repo (shows under Packages, inherits visibility)
LABEL org.opencontainers.image.source="https://github.com/zestones/Evil-Nightreign" \
      org.opencontainers.image.description="Elden Ring Nightreign relic build optimizer (fan-made)"
# openssl decrypts uploaded saves (POST /api/collection); no Python deps needed
RUN apt-get update && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY nightreign/ ./nightreign/
COPY data/ ./data/
# the freshly built SPA (base /app/ → served under /app/ by the server)
COPY --from=web /web/dist ./nightreign/ui/static/app
RUN useradd -m app && chown -R app /app
USER app
# HOST=0.0.0.0 to accept external traffic; PORT is injected by the host (Render).
# PYTHONUNBUFFERED so the "loading…/ready" logs appear immediately (otherwise a
# container looks frozen while stdout is buffered).
ENV HOST=0.0.0.0 PORT=8377 PYTHONUNBUFFERED=1
EXPOSE 8377
CMD ["python", "-m", "nightreign", "ui", "--no-browser"]
