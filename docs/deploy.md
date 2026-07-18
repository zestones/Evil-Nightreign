# Deploying to Render (free)

The server is pure Python stdlib (no framework deps) and serves both the API and the built SPA, so any host that runs a Docker image works. The one wrinkle: the runtime game data (`data/raw/*` subset) and the built SPA are gitignored, so they exist only on your machine — a from-git build on the host would miss them. Build the image **where the data lives** (your machine) and let Render run it.

## What the image contains

`Dockerfile` is multi-stage: stage 1 builds the SPA with Node; stage 2 is a slim Python image with `openssl` (needed to decrypt uploaded saves) and the game data baked in. It runs `python -m nightreign ui --no-browser`, which reads `HOST` and `PORT` from the environment (`HOST=0.0.0.0`, `PORT` injected by Render). No `pip install` — the package is stdlib-only and runs from `/app`.

## Test the image locally first

```bash
docker build -t evilnightreign .
docker run --rm -p 8377:8377 -e PORT=8377 evilnightreign
# open http://127.0.0.1:8377
```

## Option A — build & push to GHCR (recommended: keeps the repo clean, ships the visuals)

The extracted game data and icons stay inside the image, never in your public repo. Push to the GitHub Container Registry (GitHub Packages).

```bash
# one-time: a GitHub PAT with the write:packages scope, then log in
echo "$GHCR_PAT" | docker login ghcr.io -u zestones --password-stdin

docker build -t ghcr.io/zestones/evil-nightreign:latest .
docker push  ghcr.io/zestones/evil-nightreign:latest
```

A new GHCR package is **private**. Make it public so Render can pull it without credentials: on GitHub, open **Packages → `evil-nightreign` → Package settings → Change visibility → Public** (or keep it private and add the registry credentials in Render).

Then in Render: **New → Web Service → Deploy an existing image**, paste `ghcr.io/zestones/evil-nightreign:latest`. Render injects `PORT`; the image already sets `HOST=0.0.0.0`. Pick the **Free** instance type. No environment variables to add.

To ship an update: rebuild, push the same tag, and hit **Manual Deploy**.

## Option B — git-based build (auto-deploy on push, but commits game data)

Render builds the `Dockerfile` from a connected repo on every push. Because `data/raw/*` is gitignored, you must commit the runtime subset first (8 files; `data/curated/*` is already tracked, and the SPA is built in the image):

```bash
git add -f data/raw/{weapons,reinforce_weapon,calc_correct_graph,attack_element_correct,hero_stats,npc_params,custom_weapons,motion_values}.json
```

Then in Render: **New → Web Service**, connect the repo, Runtime **Docker**, instance **Free**. Render reads `PORT` and the baked `HOST=0.0.0.0`. This commits extracted game stats to your repo — fine for a fan tool, but Option A avoids it.

## Env vars

| Var | Value | Set by |
|---|---|---|
| `HOST` | `0.0.0.0` | baked into the image |
| `PORT` | (the listen port) | injected by Render |

## Caveats

- **Cold starts**: the Render Free tier sleeps after ~15 min idle and takes ~30 s to wake. Fine for a hobby tool.
- **Save privacy**: visitors upload `NR0000.sl2` (contains a SteamID). The server decodes it to relics in memory, cleans up its temp files, and never persists the save. Say so on the page.
- **Session cache** is per-process (in-memory, capped, TTL); a restart drops it, so users re-import. Fine for a single free instance.
- **Copyright**: the image ships extracted game data (params, relic/effect names, boss stats). Standard for a non-commercial fan tool, but keep it non-commercial and add a "not affiliated with FromSoftware / Bandai Namco; assets © their owners" note. Never ship `inputs/regulation.bin` (the game binary) — `.dockerignore` already excludes it.
