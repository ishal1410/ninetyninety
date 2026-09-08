#!/bin/bash
# NinetyNinety on Amazon EC2: cloud-init user data for Amazon Linux 2023.
#
# Paste this whole file into "Advanced details > User data" when launching a
# t3.small with the Amazon Linux 2023 AMI and a security group that allows
# inbound TCP 80. Replace the GOOGLE_API_KEY placeholder first.
#
# Progress: sudo tail -f /var/log/cloud-init-output.log
# App logs: sudo journalctl -u ninetyninety -f
set -euxo pipefail

# ---- edit this line before launching ----------------------------------------
GOOGLE_API_KEY="PASTE_YOUR_GEMINI_KEY_HERE"   # free key: https://aistudio.google.com/apikey
# -----------------------------------------------------------------------------

REPO="https://github.com/ishal1410/ninetyninety"
APP_DIR="/opt/ninetyninety"
APP_USER="ninetyninety"

if [ "$GOOGLE_API_KEY" = "PASTE_YOUR_GEMINI_KEY_HERE" ]; then
  echo "WARNING: GOOGLE_API_KEY is still the placeholder; edit $APP_DIR/.env and restart the service." >&2
fi

dnf install -y python3.12 git

# Non-root service account that owns the checkout (the app writes data/ and a
# temp dir per run) and never gets a login shell.
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --home-dir "$APP_DIR" --shell /sbin/nologin "$APP_USER"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 "$REPO" "$APP_DIR"
fi

python3.12 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# Same file python-dotenv reads locally (src/ninetyninety/config.py) and
# systemd reads via EnvironmentFile. Root-owned, readable only by the service user.
cat > "$APP_DIR/.env" <<EOF
GOOGLE_API_KEY=$GOOGLE_API_KEY
# Optional: GEMINI_MODEL_IDS=gemini-3.8-flash,gemini-3.5-flash,gemini-3.6-flash,gemini-3.7-flash,gemini-3.5-flash-lite
EOF
chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

cat > /etc/systemd/system/ninetyninety.service <<EOF
[Unit]
Description=NinetyNinety Streamlit app
After=network-online.target
Wants=network-online.target

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
Environment=HOME=$APP_DIR
Environment=STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ExecStart=$APP_DIR/.venv/bin/streamlit run app.py --server.port 80 --server.address 0.0.0.0 --server.headless true
Restart=on-failure
RestartSec=5
# Port 80 as a non-root user.
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ninetyninety
systemctl --no-pager status ninetyninety || true
