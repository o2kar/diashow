#!/usr/bin/env bash
# Installs the Diashow slideshow webapp on Raspberry Pi OS (Lite) under /opt/diashow
# and registers it as a systemd service that starts on boot.
#
# Run from within the project directory (the one containing this deploy/ folder), e.g.:
#   sudo bash deploy/install.sh
set -euo pipefail

APP_DIR="/opt/diashow"
SERVICE_USER="${SUDO_USER:-pi}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root (sudo bash deploy/install.sh)" >&2
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

apt-get update
apt-get install -y python3 python3-venv python3-pip rsync

mkdir -p "$APP_DIR"
rsync -a --delete --exclude 'venv' --exclude 'data' --exclude '.git' "$SOURCE_DIR"/ "$APP_DIR"/

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

mkdir -p "$APP_DIR/data/slideshows"

if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  sed -i "s/^SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" "$APP_DIR/.env"
  echo
  echo "Created $APP_DIR/.env with a generated SECRET_KEY."
  echo "You still need to set ADMIN_PASSWORD_HASH. Generate it with:"
  echo "  $APP_DIR/venv/bin/python -c \"from werkzeug.security import generate_password_hash; print(generate_password_hash('yourpassword'))\""
  echo "Then edit $APP_DIR/.env and set ADMIN_PASSWORD_HASH to the printed value."
fi

chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

sed "s/^User=.*/User=${SERVICE_USER}/" "$SOURCE_DIR/deploy/slideshow.service" > /etc/systemd/system/slideshow.service

systemctl daemon-reload
systemctl enable slideshow.service

echo
echo "Installed. Set ADMIN_PASSWORD_HASH in $APP_DIR/.env (see above), then start the service with:"
echo "  sudo systemctl start slideshow"
echo "  sudo systemctl status slideshow"
