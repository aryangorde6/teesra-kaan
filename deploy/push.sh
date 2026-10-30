#!/usr/bin/env bash
# From the laptop, in teesra-kaan/: deploy/push.sh ubuntu@<elastic-ip>
# Copies the code (never .env, data/ or the venv), installs it, restarts the service.
set -euo pipefail
host="$1"
rsync -az --delete --exclude .git --exclude .venv --exclude data --exclude runs --exclude private \
  --exclude .env --exclude '__pycache__' ./ "$host:/opt/teesrakaan/"
ssh "$host" bash -s <<'REMOTE'
set -euo pipefail
cd /opt/teesrakaan
[ -d .venv ] || python3.12 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e '.[web]'
sudo cp deploy/teesrakaan.service /etc/systemd/system/teesrakaan.service
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
# The public page has no API key (deploy/README.md, step 7); the file only has to exist for systemd.
[ -f .env ] || sudo touch .env
if sudo grep -q '^MODEL_API_KEY=.' .env; then echo "The public page must not have an API key: remove it from /opt/teesrakaan/.env"; exit 1; fi
sudo chown root:teesrakaan .env && sudo chmod 640 .env
sudo systemctl daemon-reload
sudo systemctl enable --now teesrakaan
sudo systemctl restart teesrakaan caddy
sleep 2 && curl -fsS http://127.0.0.1:8000/healthz && echo " ok"
REMOTE
