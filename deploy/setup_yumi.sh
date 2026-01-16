#!/bin/bash
# Yumi Bot (Oneesan Mode) - Deployment Script
# ============================================
# Deploys a separate instance of Femmy formatted as Yumi

set -e

BOT_USER="yumi"
BOT_DIR="/opt/yumi-bot"
SERVICE_NAME="yumi-bot"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Deploying Yumi (Oneesan Mode)...${NC}"

# 1. Create User
if ! id "$BOT_USER" &>/dev/null; then
    useradd -r -s /bin/false -d "$BOT_DIR" "$BOT_USER"
fi

# 2. Setup Directory
mkdir -p "$BOT_DIR"
cp -r ./discord_bot "$BOT_DIR/"

# 3. Virtual Env
echo -e "${YELLOW}Setting up Python environment...${NC}"
python3 -m venv "$BOT_DIR/venv"
source "$BOT_DIR/venv/bin/activate"
pip install -r "$BOT_DIR/discord_bot/requirements.txt"

# 4. Create Service
echo -e "${YELLOW}Creating systemd service...${NC}"
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOL
[Unit]
Description=Yumi Discord Bot (Oneesan Mode)
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR/discord_bot
ExecStart=$BOT_DIR/venv/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# 5. Config
if [ ! -f "$BOT_DIR/discord_bot/.env" ]; then
    cp "$BOT_DIR/discord_bot/.env.example" "$BOT_DIR/discord_bot/.env"
    # Auto-lock mode
    echo "" >> "$BOT_DIR/discord_bot/.env"
    echo "# LOCKED MODE" >> "$BOT_DIR/discord_bot/.env"
    echo "BOT_MODE=oneesan" >> "$BOT_DIR/discord_bot/.env"
    
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR/discord_bot/.env"
    chmod 600 "$BOT_DIR/discord_bot/.env"
fi

# Permissions
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
systemctl daemon-reload

echo -e "${GREEN}Done!${NC}"
echo "1. Edit config: sudo nano $BOT_DIR/discord_bot/.env"
echo "   (Add your NEW discord token here!)"
echo "2. Start: sudo systemctl start $SERVICE_NAME"
