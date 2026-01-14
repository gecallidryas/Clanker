#!/bin/bash
# Femmy Discord Bot - Update Script
# ==================================
# Run this to update the bot after pulling new code
#
# Usage:
#   sudo ./update.sh

set -e

BOT_DIR="/opt/femmy-bot"
SERVICE_NAME="femmy-bot"

echo "Stopping bot..."
systemctl stop $SERVICE_NAME

echo "Updating code..."
cp -r ./discord_bot/* "$BOT_DIR/discord_bot/"

echo "Updating dependencies..."
source "$BOT_DIR/venv/bin/activate"
pip install -r "$BOT_DIR/discord_bot/requirements.txt"

echo "Fixing permissions..."
chown -R femmy:femmy "$BOT_DIR"

echo "Starting bot..."
systemctl start $SERVICE_NAME

echo "Done! Checking status..."
systemctl status $SERVICE_NAME --no-pager
