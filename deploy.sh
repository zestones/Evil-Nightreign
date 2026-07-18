#!/usr/bin/env bash
# One command to ship: log in to GHCR, build the image, push it, and (optionally)
# trigger a Render redeploy. Configure once in .env (see .env.example), then:
#     ./deploy.sh
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "Missing .env — copy .env.example to .env and fill it in." >&2; exit 1; }
set -a; . ./.env; set +a

: "${GHCR_USER:?set GHCR_USER in .env}"
: "${GHCR_PAT:?set GHCR_PAT in .env (a GitHub PAT with the write:packages scope)}"
IMAGE="${IMAGE:-ghcr.io/${GHCR_USER}/evil-nightreign}"
TAG="${TAG:-latest}"
REF="${IMAGE}:${TAG}"

# Use ONE docker for login + build + push (mixing `docker login` with
# `sudo docker push` is what causes the "denied" error). Fall back to sudo only
# if the daemon isn't reachable as the current user.
DOCKER="docker"
if ! docker info >/dev/null 2>&1; then
  echo "==> docker needs elevation here — using 'sudo docker'"
  DOCKER="sudo docker"
fi

echo "==> login ghcr.io as ${GHCR_USER}"
printf '%s' "${GHCR_PAT}" | $DOCKER login ghcr.io -u "${GHCR_USER}" --password-stdin

echo "==> build ${REF}"
$DOCKER build -t "${REF}" .

echo "==> push ${REF}"
$DOCKER push "${REF}"

if [ -n "${RENDER_DEPLOY_HOOK:-}" ]; then
  echo "==> triggering Render redeploy"
  curl -fsSL -X POST "${RENDER_DEPLOY_HOOK}" >/dev/null && echo "    redeploy triggered"
fi

echo
echo "Done → ${REF}"
if [ -z "${RENDER_DEPLOY_HOOK:-}" ]; then
  echo "First time on Render: New → Web Service → Deploy an existing image → ${REF}"
  echo "(then grab the service's Deploy Hook, paste it into .env, and next time it's fully automatic)"
fi
