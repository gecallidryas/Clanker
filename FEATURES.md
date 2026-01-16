# Femmy Discord Bot - Feature Summary

A highly advanced Discord bot with AI-powered conversations, multiple personalities, and deep relationship tracking.

---

## 🎭 Personality Modes

| Mode | Emoji | Description |
|------|-------|-------------|
| **Femboy** | 🎀 | Obedient, cute younger brother. Uses "Nii-chan~" and loves to please. |
| **Tsundere** | 😤 | Abrasive younger sister. "It's not like I wanted to help, baka!" |
| **Oneesan** | 💕 | Caring older sister. "Ara ara~" Checks if you've eaten. |

### Commands
- `!mode <name>` - Switch personality (femboy/tsundere/oneesan)
- `!modes` - List all available modes
- `!currentmode` - Show active personality

> **Mode Locking**: Set `BOT_MODE=oneesan` in `.env` to lock personality.

## 😈 Evil Mode (Uncensored)
Enable uncensored responses using OpenRouter (Venice AI/Nous Hermes).

### Commands
- `!evil on` - Enable Evil Mode (Uncensored)
- `!evil off` - Disable Evil Mode (Standard Safety)
- `!evil` - Check current status

**Note**: Requires `OPENROUTER_API_KEY` in settings. Evil Mode is tracked per-server.

---

## 🧠 AI Integration (Gemini)

### Multi-Key Failover
- Supports up to 10 API keys
- Automatic rotation when rate limited
- Cooldown tracking per key

### Features
- Context-aware conversations (last 20 messages / 30 minutes)
- User fact injection into prompts
- Affection-based behavior adjustment
- Relaxed safety settings for more natural responses

### Commands
- `@Femmy <message>` - Chat with the bot
- `!describe` - Analyze attached images
- `!translate <text> to <language>` - Translate text
- `!tldr [count]` - Summarize last N messages

---

## 💕 Affection System

### Relationship Levels

| Level | Points | Behavior |
|-------|--------|----------|
| Stranger | 0-49 | Polite but reserved |
| Acquaintance | 50-199 | Friendly, getting to know you |
| Friend | 200-499 | Casual, uses your name |
| Close Friend | 500-999 | Affectionate, playful, remembers details |
| Beloved | 1000+ | Deep care, attachment, protectiveness |

### How Points Change
- **Positive**: Kind messages, compliments, interactions (+1 to +5)
- **Neutral**: Normal conversation (+1)
- **Negative**: Rude messages, insults (-3 to -15)

### Commands
- `!affection [@user]` - View your/their affection level
- `!headpat` / `!hug` - Give affection (+3 points, +5 mood)

---

## 🎭 Mood System (Per Server)

| Mood | Range | Behavior |
|------|-------|----------|
| Happy | 70-100 | Energetic and cheerful |
| Neutral | 40-69 | Normal responses |
| Sad | 20-39 | Slightly melancholic |
| Neglected | 0-19 | Lonely, mentions missing you |

- Mood decays by 3 every hour without interaction
- Any message activity adds +1 mood
- Headpats/hugs add +5 mood

**Command**: `!mood` - Check current mood

---

## 📝 Memory System

### User Facts
Store facts about users that the AI will remember.

| Command | Description |
|---------|-------------|
| `!remember <fact>` | Save a fact about yourself |
| `!forget` | Clear all your facts |
| `!myinfo` | View your stored information |
| `!aboutuser @user` | View facts about another user |

### User Aliases
Associate names/nicknames with Discord users.

| Command | Description |
|---------|-------------|
| `!aka @user <alias>` | Add an alias for a user |
| `!aliases @user` | List all aliases |
| `!whois <name>` | Find user by alias |

### Cross-User Recall
Ask the bot: *"What do you remember about @username?"*  
The bot fetches their facts and responds contextually.

---

## ⏰ Reminders

| Command | Description |
|---------|-------------|
| `!remind <time> <message>` | Set a reminder |
| `!reminders` | List your active reminders |
| `!remind cancel <id>` | Cancel a reminder |

**Time formats**: `5m`, `2h`, `1d`, `tomorrow`, `next week`

---

## 🔧 Admin Commands

Server administrators can manage user data.

| Command | Description |
|---------|-------------|
| `!admin reset @user [type]` | Reset data (all/facts/affection/aliases) |
| `!admin view @user` | View complete user profile |
| `!admin setfact @user <fact>` | Add a fact for a user |
| `!admin delfact @user <id>` | Delete a specific fact |
| `!admin setaffection @user <n>` | Set affection points |

---

## 🛠️ Utility Commands

| Command | Description |
|---------|-------------|
| `!help [command]` | Show help for all/specific commands |
| `!stats` | Display bot statistics |
| `!ping` | Check bot latency |
| `!about` | Bot information |
| `!portfolio [url]` | Check website status |
| `!reload [cog]` | Reload bot modules (owner only) |

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Required
DISCORD_TOKEN=your_token
GEMINI_API_KEY=your_key

# Optional Gemini Keys (up to 10)
GEMINI_API_KEY_2=
GEMINI_API_KEY_3=

# Optional Settings
BOT_MODE=          # Lock to: femboy, tsundere, or oneesan
PORTFOLIO_URL=     # For !portfolio command
BUMP_CHANNEL_ID=   # Default channel for auto-bump reminders
```

---

## 🗄️ Database Schema

| Table | Purpose |
|-------|---------|
| `users` | User profiles, timezone, birthday |
| `user_facts` | Stored facts with source tracking |
| `user_aliases` | Name aliases for users |
| `user_affection` | Affection points and levels |
| `server_config` | Per-server settings (mode, bump channel) |
| `bot_mood` | Server mood state |
| `reminders` | Active reminders |
| `pending_facts` | Facts awaiting confirmation |
| `bot_stats` | Usage statistics |

---

## 🚀 Deployment

### Quick Start (Ubuntu)
```bash
git clone https://github.com/gecallidryas/femboi.git
cd femboi
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
sudo nano /opt/femmy-bot/discord_bot/.env  # Add tokens
sudo systemctl start femmy-bot
sudo systemctl enable femmy-bot
```

### Service Management
```bash
sudo systemctl status femmy-bot   # Check status
sudo journalctl -u femmy-bot -f   # View logs
sudo systemctl restart femmy-bot  # Restart
```

### Updating
```bash
cd ~/femboi
git pull
sudo ./deploy/update.sh
```

---

## 📊 Rate Limiting

| Type | Limit | Scope |
|------|-------|-------|
| User AI requests | 10/minute | Per user |
| Gemini API | 15/minute | Per key (free tier) |
| Commands | Varies | Per cooldown decorator |

---

## 🔒 Security Features

- `.env` files are gitignored
- Systemd service runs as dedicated user
- Memory limits (512MB) and CPU quotas
- Admin commands require `manage_guild` permission
- Owner-only reload command

---

*Built with love using Discord.py and Google Gemini AI* 💖
