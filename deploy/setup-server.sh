#!/usr/bin/env bash
# Run once on a fresh Ubuntu 24.04 server, as a user with sudo: bash setup-server.sh
set -euo pipefail
sudo apt-get update
sudo apt-get install -y python3.12-venv ffmpeg debian-keyring debian-archive-keyring apt-transport-https curl rsync
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install -y caddy
id teesrakaan >/dev/null 2>&1 || sudo useradd --system --home /opt/teesrakaan --shell /usr/sbin/nologin teesrakaan
sudo mkdir -p /opt/teesrakaan/data
sudo chown -R "$USER":teesrakaan /opt/teesrakaan
sudo chown teesrakaan:teesrakaan /opt/teesrakaan/data
echo "Server ready. Now run deploy/push.sh from the laptop."
