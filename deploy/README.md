# Femmy Discord Bot - Ubuntu ARM Deployment Guide

## 📋 Prerequisites

- Ubuntu 22.04 LTS (ARM64)
- SSH access with sudo privileges
- Discord bot token
- Gemini API key(s)

---

## 🚀 Quick Deploy (One Command)

```bash
# 1. Copy project to your ARM server
scp -r femboibot/ user@your-server:/home/user/

# 2. SSH into server
ssh user@your-server

# 3. Run deployment script
cd /home/user/femboibot
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh

# 4. Edit .env with your tokens
sudo nano /opt/femmy-bot/discord_bot/.env

# 5. Start the bot
sudo systemctl start femmy-bot
sudo systemctl enable femmy-bot
```

---

## 📁 Deployment Files

| File | Purpose |
|------|---------|
| `deploy/femmy-bot.service` | Systemd service definition |
| `deploy/deploy.sh` | Initial setup script |
| `deploy/update.sh` | Update deployed bot |

---

## 🔧 Common Commands

### Service Management

```bash
# Start the bot
sudo systemctl start femmy-bot

# Stop the bot
sudo systemctl stop femmy-bot

# Restart the bot
sudo systemctl restart femmy-bot

# Check status
sudo systemctl status femmy-bot

# Enable auto-start on boot
sudo systemctl enable femmy-bot

# Disable auto-start
sudo systemctl disable femmy-bot
```

### Logs & Monitoring

```bash
# View live logs
sudo journalctl -u femmy-bot -f

# View last 100 log lines
sudo journalctl -u femmy-bot -n 100

# View logs since last boot
sudo journalctl -u femmy-bot -b

# View logs from specific time
sudo journalctl -u femmy-bot --since "1 hour ago"
```

### Updates

```bash
# After pulling new code locally, copy to server:
scp -r discord_bot/ user@server:/home/user/femboibot/

# On server, run update script:
cd /home/user/femboibot
sudo ./deploy/update.sh
```

---

## 🔒 Security Features (Built-in)

The systemd service includes these security hardening options:

| Feature | Description |
|---------|-------------|
| Dedicated user | Runs as `femmy` user, not root |
| NoNewPrivileges | Prevents privilege escalation |
| PrivateTmp | Isolated temp directory |
| ProtectSystem | Read-only system directories |
| ProtectHome | Cannot access /home |
| MemoryMax | Limits RAM to 512MB |
| CPUQuota | Limits CPU to 50% |

---

## 🐛 Troubleshooting

### Bot won't start

```bash
# Check for errors
sudo journalctl -u femmy-bot -n 50

# Common issues:
# - Missing .env file
# - Invalid tokens in .env
# - Missing Python dependencies
```

### Permission denied

```bash
# Fix ownership
sudo chown -R femmy:femmy /opt/femmy-bot

# Fix .env permissions
sudo chmod 600 /opt/femmy-bot/discord_bot/.env
```

### Out of memory (ARM devices)

Edit the service file to reduce memory limit:
```bash
sudo nano /etc/systemd/system/femmy-bot.service
# Change: MemoryMax=256M
sudo systemctl daemon-reload
sudo systemctl restart femmy-bot
```

---

## 📊 Resource Usage

Expected resource usage on ARM:

| Resource | Idle | Active |
|----------|------|--------|
| RAM | ~80MB | ~150-300MB |
| CPU | <1% | 5-15% during AI calls |
| Disk | ~50MB | + logs over time |

---

## ✅ Verification Checklist

- [ ] Bot appears online in Discord
- [ ] `!ping` command responds
- [ ] `!help` shows all commands
- [ ] AI responses work (mention the bot)
- [ ] Logs show no errors: `sudo journalctl -u femmy-bot -n 20`
- [ ] Auto-restart works: `sudo pkill -f "python main.py"` then check status
