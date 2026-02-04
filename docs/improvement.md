# FemboiBot Feature Roadmap

> Based on feature parity analysis with TomoriBot. Last updated: 2026-02-04

---

## Executive Summary

This document outlines the implementation roadmap to enhance FemboiBot with agentic AI capabilities. The milestones below target full parity with TomoriBot (excluding NovelAI) and add a few parity-plus upgrades.

> [!NOTE]
> **Excluded Feature**: NovelAI provider integration has been intentionally excluded from this roadmap. Our current provider stack (Gemini + OpenRouter) covers all use cases including uncensored/roleplay content via OpenRouter models. Adding NovelAI would introduce unnecessary complexity without significant benefit.

---

## Current Strengths (Unique to FemboiBot)

These features give us an advantage over TomoriBot:

- ❤️ **Advanced Affection System** - 5-tier relationship tracking with mood
- ⭐ **Starboard** - Community highlight system
- 🛡️ **Auto-moderation** - Keyword rules + spam protection
- 🎂 **Birthday Tracking** - With upcoming birthdays view
- 👋 **AI Welcome Messages** - Custom per-server greetings
- ✅ **Autorole** - Automatic role assignment on join

---

## Implementation Roadmap

### Milestone 0: Tooling Foundation (Week 0-1)

**Goal**: Parity with Tomori's tool system and feature gating.

| Feature | Description | Priority |
|---------|-------------|----------|
| Tool Registry | Central registry for built-in tools and external tools | High |
| Feature Flags | Per-guild enable/disable for tools | High |
| Capability Review | AI tool to report available capabilities | High |
| Tool Context | Standard tool context (guild, channel, user, config) | High |

**Files to Create**:
- `utils/tool_registry.py` - Tool registration and dispatch
- `utils/tool_flags.py` - Feature flag mapping
- `utils/tool_context.py` - Standardized context object
- `cogs/tools_admin.py` - Admin commands for tool status

**AI Integration**:
```json
{"tool": "review_capabilities", "capability_type": "chat"}
```

---

### Milestone 1: Web Intelligence (Week 1-2)

**Goal**: Enable AI to search the web and analyze URLs (MCP + REST parity).

| Feature | Description | Priority |
|---------|-------------|----------|
| DuckDuckGo Search | Free web search, no API key | High |
| URL Fetcher | Extract content from webpages | High |
| Brave Search | Optional upgrade with better results | Medium |

**Files to Create**:
- `utils/web_search.py` - Search provider abstraction
- `utils/url_fetcher.py` - Webpage content extraction

**Dependencies**:
```
duckduckgo-search>=6.0.0
trafilatura>=1.6.0
```

**AI Integration**:
```json
{"tool": "web_search", "query": "latest anime news 2026"}
{"tool": "fetch_url", "url": "https://example.com/article"}
```

---

### Milestone 2: Media and Expression Tools (Week 2-3)

**Goal**: Match Tomori media and expression capabilities.

| Feature | Description | Priority |
|---------|-------------|----------|
| Image Generation | Generate images via OpenRouter/Replicate | High |
| Sticker Usage | AI chooses server stickers | Medium |
| Emoji Usage | AI chooses server emojis | Medium |
| Media Context Expansion | AI can request older media context | Medium |
| GIF Analysis (Dev) | Extract keyframes for analysis (dev only) | Low |

**Files to Create**:
- `cogs/imagegen.py` - Image generation cog
- `utils/expression_picker.py` - Emoji/sticker selection
- `utils/media_context.py` - Media window expansion helpers
- `utils/gif_processor.py` - Dev-only GIF keyframes

**Dependencies**:
```
REPLICATE_API_KEY=optional_for_imagegen
```

**Commands**:
- `/generate image <prompt>` - Generate an image
- Expression usage is automatic via tools

---

### Milestone 3: Content Tools (Week 3-4)

**Goal**: YouTube processing, pinning, and profile peeking.

| Feature | Description | Priority |
|---------|-------------|----------|
| YouTube Processing | Analyze YouTube with Gemini capability | Medium |
| Message Pinning | AI pins important messages | Low |
| Profile Peek | AI can view user avatars | Low |

**Files to Create**:
- `utils/youtube.py` - YouTube processing
- `cogs/tools.py` - Unified tools cog

**Dependencies**:
```
youtube-transcript-api>=0.6.0
pytube>=15.0.0
```

**AI Integration**:
```json
{"tool": "process_youtube_video", "youtube_url": "https://youtube.com/watch?v=xxx"}
{"tool": "pin_message", "message_id": 123456789}
```

---

### Milestone 4: Memory and Teaching Parity (Week 4-5)

**Goal**: Match Tomori's /teach system and self-teaching tools.

| Feature | Description | Priority |
|---------|-------------|----------|
| /teach memory | Personal and server memory teaching | High |
| /teach attribute | Personality attributes teaching | Medium |
| /teach sampledialogue | Example dialogue teaching | Medium |
| Self-Teaching Tools | AI can save/update memories | High |
| Privacy Controls | Opt-out for personal memory | Medium |

**Notes**:
- Add tool calls: `remember_this_fact`, `update_short_term_memory`, `update_long_term_memory`.
- Add `/forget` expansions to match Tomori's memory deletion coverage.

---

### Milestone 5: RAG Document Memory (Week 6-7)

**Goal**: Match Tomori's document RAG flow.

| Feature | Description | Priority |
|---------|-------------|----------|
| /teach document | Upload and store docs for retrieval | Medium |
| Retrieval | Inject relevant doc chunks at chat time | Medium |
| Vector Store | pgvector on Postgres or ChromaDB | Medium |

**Notes**:
- Gate local RAG behind an env flag (parity with Tomori).
- Enforce file size, chunk count, and per-server limits.

---

### Milestone 6: Multi-Persona and Webhooks (Not required)

**Decision**: Not needed for FemboiBot.

**Why**:
- We use a single active persona (mode switching), not multiple personas at once.
- Persona changes are applied by updating the bot's per-server profile, not via webhooks.

**Result**: This milestone is skipped. All other milestones remain in scope.

---

### Milestone 7: Internationalization (Week 9)

**Goal**: Support multiple languages.

| Feature | Description | Priority |
|---------|-------------|----------|
| i18n System | Locale-based string loading | Low |
| English Locale | Default language file | Low |
| Japanese Locale | Secondary language | Low |

**Files to Create**:
- `locales/en.json` - English strings
- `locales/ja.json` - Japanese strings
- `utils/i18n.py` - Localization utilities

**Usage**:
```python
from utils.i18n import t
await ctx.send(t("reminder.set", locale="ja", time="30m"))
```

---

### Milestone 8: Custom Endpoint Provider (Week 10)

**Goal**: Optional parity with Tomori's custom OpenAI-compatible endpoint.

| Feature | Description | Priority |
|---------|-------------|----------|
| Custom Provider | OpenAI-compatible endpoint (self-hosted) | Low |
| Capability Flags | User-declared tools/vision/video support | Low |

---

### Milestone 9: Parity-Plus Enhancements (Week 11+)

**Goal**: Go beyond TomoriBot with optional improvements.

| Feature | Description | Priority |
|---------|-------------|----------|
| GIF Responses | Optional Tenor/Giphy integration for AI replies | Low |
| Advanced Safety | URL phishing checks, regex allow/deny lists | Medium |
| Cost/Usage Dashboard | Track API spend, tool usage, and limits | Low |
| Config UI | Web dashboard for guild settings | Low |

## Explicitly Excluded

> [!IMPORTANT]
> **NovelAI Provider** - Will NOT be implemented.
> 
> Reasoning:
> - OpenRouter already provides access to roleplay-focused models (Claude, Mistral, etc.)
> - NovelAI uses a proprietary API format requiring significant custom work
> - Cost/benefit ratio is unfavorable
> - Our dual-provider setup (Gemini + OpenRouter) covers all use cases

> **Multi-Persona + Webhooks** - Not required.
>
> Reasoning:
> - FemboiBot uses a single active persona via mode switching.
> - Profile changes are applied to the bot's per-server profile instead of webhook identity.

---

## Timeline Summary

Week 0-1: M0 Tooling Foundation
Week 1-2: M1 Web Intelligence
Week 2-3: M2 Media and Expression Tools
Week 3-4: M3 Content Tools
Week 4-5: M4 Memory and Teaching
Week 6-7: M5 RAG Document Memory
Week 8:   (skipped) Multi-Persona and Webhooks not required
Week 9:   M7 Internationalization
Week 10:  M8 Custom Endpoint Provider (optional)
Week 11+: M9 Parity-Plus Enhancements

**Total: ~10+ weeks**

## Success Metrics

| Metric | Target |
|--------|--------|
| Web searches/day | Track usage |
| Images generated/week | Track usage |
| Memory recall accuracy | >80% relevant |
| User satisfaction | Feedback collection |

---

## Getting Started

1. Review this document
2. Create feature branches for each milestone
3. Implement with tests
4. Deploy to staging
5. Collect feedback
6. Push to production

**First Step**: Begin Milestone 0 (Tooling Foundation)
