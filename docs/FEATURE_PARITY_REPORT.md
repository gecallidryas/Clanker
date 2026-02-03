# Feature Parity Report: FemboiBot vs TomoriBot

A comprehensive comparison of features between **FemboiBot** (Python/discord.py) and **TomoriBot** (TypeScript/discord.js).

---

## Summary

| Category | FemboiBot | TomoriBot | Parity |
|----------|-----------|-----------|--------|
| Core AI Chat | ✅ | ✅ | ✅ Match |
| Memory System | ✅ Unified | ✅ Long/Short Term | ⚠️ TomoriBot more advanced |
| Persona System | ✅ | ✅ | ✅ Match |
| Multi-Provider AI | ⚠️ Gemini + OpenRouter | ✅ Gemini + OpenRouter + NovelAI | ⚠️ Partial |
| Affection Tracking | ✅ Advanced | ❌ | ✅ FemboiBot ahead |
| Image Analysis | ✅ Gemini Vision | ✅ | ✅ Match |
| Image Generation | ❌ | ✅ | ❌ Missing |
| Web Search | ❌ | ✅ MCP (Brave/DuckDuckGo) | ❌ Missing |
| Reminders | ✅ | ✅ | ✅ Match |
| Starboard | ✅ | ❌ | ✅ FemboiBot ahead |
| Automoderation | ✅ | ❌ | ✅ FemboiBot ahead |
| YouTube Tool | ❌ | ✅ | ❌ Missing |
| Sticker/GIF Tools | ❌ | ✅ | ❌ Missing |
| Message Pinning | ❌ | ✅ AI-controlled | ❌ Missing |
| RAG/Document Memory | ❌ | ✅ pgvector | ❌ Missing |
| Localization | ❌ | ✅ i18n | ❌ Missing |

---

## Detailed Feature Breakdown

### 🧠 AI & Chat Features

#### FemboiBot
- **Core AI**: Gemini API integration with context management
- **Context Window**: 30-minute rolling context (deque-based)
- **Agentic Actions**: JSON-based admin actions (moderation, config changes)
- **Evil Mode**: OpenRouter uncensored model switching
- **Trigger**: Mentions or configurable trigger words

#### TomoriBot
- **Core AI**: Multi-provider (Google Gemini, OpenRouter, NovelAI)
- **Context**: Conversation history with long/short term memory separation
- **Tool System**: Extensive function calling with MCP integration
- **Streaming**: Real-time response streaming
- **Trigger**: Configurable trigger words + mentions

> [!IMPORTANT]
> TomoriBot has a more sophisticated tool/function calling system with 13+ built-in tools.

---

### 💾 Memory Systems

#### FemboiBot
| Feature | Details |
|---------|---------|
| User Facts | Store personal info via `!remember` |
| Timezones | IANA timezone storage |
| Birthdays | Birthday tracking with upcoming view |
| Aliases | User nickname management (`!aka`, `!whois`) |
| AI Summarization | Facts are AI-summarized to remove conflicts |

#### TomoriBot
| Feature | Details |
|---------|---------|
| Short-term Memory | Recent conversation context |
| Long-term Memory | Persistent facts via `/teach` commands |
| RAG Support | Optional pgvector for document retrieval |
| Memory Tools | AI can create/update memories dynamically |
| Export/Import | Data portability features |

> [!NOTE]
> FemboiBot has birthday and alias features that TomoriBot lacks.

---

### 🎭 Persona & Mode System

#### FemboiBot
- **Built-in Modes**: Femboy, Tsundere, Oneesan
- **Custom Personas**: Admin-created with:
  - Custom name, avatar, banner
  - Normal and "evil mode" prompts
  - Rate-limited creation (3/hour, 5 per guild)
- **Mode Lock**: Environment variable to lock bot to specific mode
- **Server Avatar**: Changes bot avatar per mode

#### TomoriBot
- **Presets**: Pre-configured personalities
- **Custom Personas**: Via `/persona` commands
- **Export/Import**: Character card style sharing
- **Attributes**: Detailed attribute and sample dialogue system

---

### 🛠️ Tools & Capabilities

#### FemboiBot Tools
```
Vision Analysis     ✅ Gemini Vision for images
Translation         ✅ AI-powered translation
Summarization       ✅ Message history TLDR
Reminders           ✅ Natural time parsing
Embed Generation    ✅ AI-generated embeds
```

#### TomoriBot Tools (13+ function calls)
```
generateImage       ✅ AI image generation
youtubeVideo        ✅ YouTube video analysis
memoryTool          ✅ Dynamic memory creation
reminderTool        ✅ Set reminders
stickerTool         ✅ Use server stickers
processGif          ✅ GIF handling
pinMessage          ✅ AI-controlled pinning
peekProfilePicture  ✅ View user avatars
increaseMediaContext ✅ Request more media context
reviewCapabilities  ✅ Self-capability review
```

#### TomoriBot MCP Servers
```
Brave Search        ✅ Web search (requires API key)
DuckDuckGo Search   ✅ Fallback web search
URL Fetch           ✅ Webpage content analysis
```

> [!CAUTION]
> FemboiBot is missing significant agentic capabilities: Image Generation, Web Search, YouTube, and AI-controlled message pinning.

---

### 👥 User Engagement

#### FemboiBot Affection System
| Level | Points | Behavior Context |
|-------|--------|------------------|
| Stranger | 0-49 | Distant, cautious |
| Acquaintance | 50-199 | Friendly, warming up |
| Friend | 200-499 | Comfortable, helpful |
| Close Friend | 500-999 | More personal |
| Beloved | 1000+ | Deep attachment |

Additional features:
- **Mood Tracking**: Happy, Neutral, Sad, Neglected states
- **Mood Decay**: Automatic mood decay when inactive
- **Interactions**: `!headpat`, `!hug` with rate limits
- **Sentiment Analysis**: Message sentiment affects affection
- **Mode-specific Traits**: Per-mode affection modifiers

#### TomoriBot
- No equivalent affection/mood system

---

### ⚙️ Server Configuration

#### FemboiBot
- **API Keys**: Multi-slot Gemini keys (5 slots), OpenRouter keys (5 slots)
- **Per-category Keys**: General, Translate, Vision, Profile, Uncensored
- **Model Selection**: Per-category model configuration
- **Password Protection**: Guild config password system
- **Env Upload**: Upload `.env` file to configure

#### TomoriBot
- **API Keys**: Per-server encrypted key storage
- **Provider Selection**: Switch between Gemini/OpenRouter/NovelAI
- **Feature Toggles**: Stickers, web search, self-teaching, pin messages, imagegen
- **Localization**: Multi-language support

---

### 🛡️ Moderation Features

#### FemboiBot (Unique)
- **Starboard**: Customizable emoji triggers, thresholds, self-star toggle
- **Automod**: Keyword rules with actions (delete/timeout/kick/ban)
- **Spam Protection**: Configurable message rate limiting
- **Mod Log**: Dedicated logging channel
- **Staff Roles**: Designate staff exempt from automod
- **Welcome System**: Customizable AI-powered welcome messages
- **Autorole**: Automatic role assignment on join

#### TomoriBot
- `/server` commands for permission management
- No built-in starboard or automod

---

### 📊 Admin & Data Management

#### FemboiBot
- Reset user data (facts, affection, aliases)
- View complete user profiles
- Set/delete individual facts
- Adjust affection points
- Gender role mapping
- Command sync management

#### TomoriBot
- `/data` commands for export/delete
- `/forget` commands to remove memories
- Legal compliance (privacy policy, terms)

---

## Gap Analysis: Features to Add to FemboiBot

### High Priority (Core Parity)
1. **Image Generation Tool**
   - Provider: Use existing OpenRouter or add dedicated provider
   - Implementation: New cog with `/generate image` command

2. **Web Search Capability**
   - Option A: MCP integration like TomoriBot
   - Option B: Direct API (Brave, DuckDuckGo, SerpAPI)
   - Use case: AI can search for current information

3. **YouTube Video Analysis**
   - Fetch video metadata, transcripts
   - AI can summarize/discuss videos

### Medium Priority (Enhanced Features)
4. **Long/Short Term Memory Separation**
   - Short-term: Current context window
   - Long-term: Persistent facts (already exists, needs tagging)

5. **AI-Controlled Message Pinning**
   - Let AI pin important messages when appropriate

6. **Sticker/GIF Usage**
   - AI can react with server stickers
   - GIF responses

7. **NovelAI Provider**
   - Alternative for roleplay-focused generation

### Lower Priority (Nice to Have)
8. **Localization (i18n)**
   - Multi-language command responses

9. **RAG/Document Memory**
   - pgvector integration for document retrieval

10. **Profile Picture Viewing**
    - AI can peek at user avatars for context

---

## Features Where FemboiBot Leads

1. **Affection & Mood System** - Deep relationship tracking
2. **Starboard** - Community highlight feature  
3. **Automoderation** - Keyword rules, spam protection
4. **Birthday Tracking** - With upcoming birthdays view
5. **User Aliases** - `!aka` and `!whois` for nicknames
6. **Welcome System** - AI-powered custom welcomes
7. **Mode-specific Avatars** - Bot avatar changes per persona

---

## Technical Comparison

| Aspect | FemboiBot | TomoriBot |
|--------|-----------|-----------|
| Language | Python 3 | TypeScript |
| Framework | discord.py | discord.js |
| Database | SQLite (per-guild) | PostgreSQL |
| AI Provider | Google Gemini, OpenRouter | Google Gemini, OpenRouter, NovelAI |
| Encryption | AES (Fernet) | pgcrypto |
| Deployment | Manual/Scripts | Docker Compose |
| Monitoring | File logging | Grafana optional |

---

## Recommendations

### Short-term (1-2 weeks)
1. Add web search capability (highest impact)
2. Implement image generation tool

### Medium-term (1 month)
3. Add YouTube video tool
4. Implement sticker/GIF usage
5. Add AI message pinning

### Long-term
6. Consider PostgreSQL migration for RAG
7. Add i18n support
8. NovelAI provider integration
