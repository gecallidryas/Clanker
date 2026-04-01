#!/bin/bash
# Femmy Discord Bot - Ubuntu 22.04 ARM Deployment Script
# ========================================================
# Run this script on your ARM server to set up the bot
#
# Usage:
#   chmod +x deploy.sh
#   sudo ./deploy.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Femmy Discord Bot - Deployment Setup ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run this script as root (sudo ./deploy.sh)${NC}"
    exit 1
fi

# Variables
BOT_USER="femmy"
BOT_DIR="/opt/femmy-bot"
SERVICE_NAME="femmy-bot"

echo -e "${YELLOW}[1/7] Installing system dependencies...${NC}"
apt update
apt install -y python3 python3-pip python3-venv git

echo -e "${YELLOW}[2/7] Creating bot user...${NC}"
if id "$BOT_USER" &>/dev/null; then
    echo "User $BOT_USER already exists"
else
    useradd -r -s /bin/false -d "$BOT_DIR" "$BOT_USER"
    echo "Created user $BOT_USER"
fi

echo -e "${YELLOW}[3/7] Setting up bot directory...${NC}"
mkdir -p "$BOT_DIR"

# Check if we're copying from current directory or cloning
if [ -f "./discord_bot/main.py" ]; then
    echo "Copying bot files from current directory..."
    cp -r ./discord_bot "$BOT_DIR/"
else
    echo -e "${RED}Error: discord_bot directory not found in current path${NC}"
    echo "Please run this script from the femboibot project root"
    exit 1
fi

echo -e "${YELLOW}[4/7] Creating Python virtual environment...${NC}"
python3 -m venv "$BOT_DIR/venv"
source "$BOT_DIR/venv/bin/activate"

echo -e "${YELLOW}[5/7] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r "$BOT_DIR/discord_bot/requirements.txt"

# Create logs directory
mkdir -p "$BOT_DIR/discord_bot/logs"

echo -e "${YELLOW}[6/7] Setting up systemd service...${NC}"
# Copy service file
cp ./deploy/femmy-bot.service /etc/systemd/system/

# Set permissions
chown -R "$BOT_USER:$BOT_USER" "$BOT_DIR"
chmod 600 "$BOT_DIR/discord_bot/.env" 2>/dev/null || true

# Reload systemd
systemctl daemon-reload

echo -e "${YELLOW}[7/7] Final setup...${NC}"

# Check if .env exists
if [ ! -f "$BOT_DIR/discord_bot/.env" ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp "$BOT_DIR/discord_bot/.env.example" "$BOT_DIR/discord_bot/.env"
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR/discord_bot/.env"
    chmod 600 "$BOT_DIR/discord_bot/.env"
    echo -e "${RED}⚠️  IMPORTANT: Edit /opt/femmy-bot/discord_bot/.env with your tokens!${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!                 ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. Edit .env file with your tokens:"
echo -e "     ${YELLOW}sudo nano $BOT_DIR/discord_bot/.env${NC}"
echo ""
echo -e "  2. Start the bot:"
echo -e "     ${YELLOW}sudo systemctl start $SERVICE_NAME${NC}"
echo ""
echo -e "  3. Enable auto-start on boot:"
echo -e "     ${YELLOW}sudo systemctl enable $SERVICE_NAME${NC}"
echo ""
echo -e "Useful commands:"
echo -e "  Check status:  ${YELLOW}sudo systemctl status $SERVICE_NAME${NC}"
echo -e "  View logs:     ${YELLOW}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  Restart:       ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}"
echo -e "  Stop:          ${YELLOW}sudo systemctl stop $SERVICE_NAME${NC}"
echo ""
