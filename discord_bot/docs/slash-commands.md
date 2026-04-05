# Slash Commands

This file documents the slash commands currently defined by the bot.

- Total slash commands: `152`
- Source of truth: `discord_bot/cogs/*.py`
- Commands are loaded dynamically from all cogs during startup

Some commands require elevated Discord permissions such as `Manage Guild`, `Administrator`, or bot owner access.

## General

| Command | Description | Source |
| --- | --- | --- |
| `/about` | Display information and stats about the bot. | `utilities.py` |
| `/generate_embed` | Describe an embed and I'll build it. | `utilities.py` |
| `/help` | Show help for commands. | `utilities.py` |
| `/ping` | Check bot latency. | `utilities.py` |
| `/reload` | Reload a cog or all cogs (owner only). | `utilities.py` |
| `/tldr` | Summarize the last N messages. | `utilities.py` |
| `/translate` | Translate text to another language. | `utilities.py` |
| `/usage` | Display usage dashboard. | `usage.py` |

## Social And Persona

| Command | Description | Source |
| --- | --- | --- |
| `/affection` | View your or another user's affection level. | `affection.py` |
| `/evil` | Toggle uncensored (evil) mode. | `social.py` |
| `/headpat` | Give a headpat. | `affection.py` |
| `/hug` | Give a hug. | `affection.py` |
| `/mood` | Check the bot's current mood. | `affection.py` |
| `/persona delete` | Delete a custom persona. | `persona.py` |
| `/persona edit` | Edit a custom persona. | `persona.py` |
| `/persona manage` | Open the persona and presentation admin panel. | `persona.py` |

## Vision And Media

| Command | Description | Source |
| --- | --- | --- |
| `/describe` | Describe an attached image. | `vision.py` |
| `/generate image` | Generate an image from a prompt. | `imagegen.py` |

## Memory And Profiles

| Command | Description | Source |
| --- | --- | --- |
| `/aboutuser` | View facts about another user. | `memories.py` |
| `/aka` | Add an alias for a user. | `memories.py` |
| `/aliases` | List aliases for a user. | `memories.py` |
| `/analyze` | Get a fun, AI-generated summary of someone's personality based on their messages. | `memories.py` |
| `/birthday` | View or set birthdays. | `memories.py` |
| `/forget` | Clear stored memory. | `memories.py` |
| `/myinfo` | View your stored timezone and facts. | `memories.py` |
| `/remember personal` | Save a personal fact. | `memories.py` |
| `/remember server` | Save a server memory. | `memories.py` |
| `/timezone` | Set your timezone. | `memories.py` |
| `/whois` | Find a user by alias. | `memories.py` |

## Reminders And Scheduling

| Command | Description | Source |
| --- | --- | --- |
| `/bumpchannel` | Set the channel for bump reminders. | `scheduler.py` |
| `/bumpstart` | Enable bump reminders. | `scheduler.py` |
| `/bumpstop` | Disable bump reminders. | `scheduler.py` |
| `/remind` | Set a reminder. | `reminders.py` |
| `/remindcancel` | Cancel a reminder by ID. | `reminders.py` |
| `/reminders` | List your active reminders. | `reminders.py` |

## Teaching

| Command | Description | Source |
| --- | --- | --- |
| `/personal privacy` | Opt in or out of personal memory. | `teach.py` |
| `/teach attribute` | Teach a persona attribute. | `teach.py` |
| `/teach document` | Upload a document for RAG memory. | `teach.py` |
| `/teach sampledialogue` | Teach a sample dialogue line. | `teach.py` |

## Moderation And Community

| Command | Description | Source |
| --- | --- | --- |
| `/automod add` | Add or update an automod rule. | `automod.py` |
| `/automod list` | List automod rules. | `automod.py` |
| `/automod remove` | Remove an automod rule. | `automod.py` |
| `/automod spam` | Configure automod spam timeout. | `automod.py` |
| `/starboard ignore` | Ignore a channel for starboard. | `starboard.py` |
| `/starboard ignored` | List ignored channels. | `starboard.py` |
| `/starboard setup` | Configure starboard for this server. | `starboard.py` |
| `/starboard toggle` | Enable or disable starboard. | `starboard.py` |
| `/starboard unignore` | Remove a channel from the ignore list. | `starboard.py` |

## Admin

| Command | Description | Source |
| --- | --- | --- |
| `/admin affection` | Set affection points for a user. | `admin.py` |
| `/admin clearglobal` | Clear all global slash commands (owner only). | `admin.py` |
| `/admin clearguild` | Clear all guild-specific slash commands for this server. | `admin.py` |
| `/admin delfact` | Delete a fact by ID. | `admin.py` |
| `/admin model` | Change the active AI model. | `admin.py` |
| `/admin reset` | Reset user data. | `admin.py` |
| `/admin setfact` | Add a fact for a user. | `admin.py` |
| `/admin view` | View a user's profile. | `admin.py` |
| `/avatar reset` | Reset to the default server avatar. | `admin.py` |
| `/setgenderrole` | Configure a gender role for this server. | `admin.py` |

## Guild Management

| Command | Description | Source |
| --- | --- | --- |
| `/autorole manage` | Open the autorole section inside the config panel UX. | `config.py` |
| `/modlog clear` | Disable moderation logs. | `config.py` |
| `/modlog manage` | Open the mod-log section inside the config panel UX. | `config.py` |
| `/modlog set` | Set the moderation log channel. | `config.py` |
| `/modlog view` | View the current mod log channel. | `config.py` |
| `/staff add` | Add a role as bot staff. | `config.py` |
| `/staff list` | List configured bot staff roles. | `config.py` |
| `/staff manage` | Open the staff section inside the config panel UX. | `config.py` |
| `/staff remove` | Remove a role from bot staff. | `config.py` |
| `/welcome channel` | Set the welcome channel. | `config.py` |
| `/welcome clear` | Disable welcome messages and clear the channel. | `config.py` |
| `/welcome clear_dm_message` | Clear the DM welcome message. | `config.py` |
| `/welcome clear_message` | Clear the welcome message template. | `config.py` |
| `/welcome manage` | Open the welcome section inside the config panel UX. | `config.py` |
| `/welcome set_dm_message` | Set the DM welcome message. | `config.py` |
| `/welcome set_message` | Set a custom welcome message template. | `config.py` |
| `/welcome test` | Send a test welcome message. | `config.py` |
| `/welcome toggle_dm` | Enable or disable DM welcome messages. | `config.py` |
| `/welcome view_message` | View the welcome message template. | `config.py` |

## Config

| Command | Description | Source |
| --- | --- | --- |
| `/config ai auto_channel_add` | Add a channel to AI auto-response channels. | `config.py` |
| `/config ai auto_channel_remove` | Remove a channel from AI auto-response channels. | `config.py` |
| `/config ai auto_threshold` | Set message count threshold for auto channels. | `config.py` |
| `/config ai cooldown` | Set AI reply cooldown in seconds. | `config.py` |
| `/config ai cooldown_type` | Set AI reply cooldown scope. | `config.py` |
| `/config ai self_reply_limit` | Set max self-reply chain depth. | `config.py` |
| `/config ai stream_budget` | Set streaming flush and send-budget limits. | `config.py` |
| `/config ai streaming` | Enable or disable streamed AI replies. | `config.py` |
| `/config ai thought_channel` | Set or clear the dedicated AI thought/debug channel. | `config.py` |
| `/config ai thought_level` | Set AI thought/debug logging level. | `config.py` |
| `/config ai thought_modlog` | Allow or deny fallback reuse of the mod-log for AI thought logs. | `config.py` |
| `/config ai view` | View AI reply gating settings. | `config.py` |
| `/config ai whitelist_add` | Add a channel to the AI reply whitelist. | `config.py` |
| `/config ai whitelist_clear` | Clear the AI reply whitelist. | `config.py` |
| `/config ai whitelist_remove` | Remove a channel from the AI reply whitelist. | `config.py` |
| `/config auth` | Authenticate for sensitive config operations. | `config.py` |
| `/config custom_endpoint set` | Set custom endpoint values. | `config.py` |
| `/config custom_endpoint view` | View custom endpoint settings. | `config.py` |
| `/config env example` | Send the guild .env.example template. | `config.py` |
| `/config env upload` | Upload a .env file for this guild. | `config.py` |
| `/config keys clear` | Clear all stored API keys. | `config.py` |
| `/config keys set` | Set an API key for a task. | `config.py` |
| `/config keys view` | View masked API keys. | `config.py` |
| `/config model set` | Set a model for a provider. | `config.py` |
| `/config model view` | View current model settings. | `config.py` |
| `/config panel` | Open the primary Discord-native config panel. | `config.py` |
| `/config password change` | Change the config password. | `config.py` |
| `/config password reset` | Reset the config password (owner only). | `config.py` |
| `/config password set` | Set the config password (first time only). | `config.py` |
| `/config toggle autorole` | Enable or disable auto-role. | `config.py` |
| `/config toggle emojis` | Enable or disable emoji usage. | `config.py` |
| `/config toggle evil` | Enable or disable evil mode. | `config.py` |
| `/config toggle gif_responses` | Enable or disable GIF replies. | `config.py` |
| `/config toggle image_gen` | Enable or disable image generation. | `config.py` |
| `/config toggle pin_message` | Enable or disable AI pinning. | `config.py` |
| `/config toggle profile_peek` | Enable or disable profile picture analysis. | `config.py` |
| `/config toggle rag` | Enable or disable local RAG retrieval. | `config.py` |
| `/config toggle self_teaching` | Enable or disable self-teaching. | `config.py` |
| `/config toggle stickers` | Enable or disable sticker usage. | `config.py` |
| `/config toggle url_safety` | Enable or disable URL safety checks. | `config.py` |
| `/config toggle web_search` | Enable or disable web search tools. | `config.py` |
| `/config toggle welcome` | Enable or disable welcome messages. | `config.py` |
| `/config toggle youtube` | Enable or disable YouTube processing. | `config.py` |
| `/config ui` | Open a quick toggle UI panel. | `config.py` |
| `/config url_safety action` | Set URL safety action (warn/delete). | `config.py` |
| `/config url_safety allowlist` | Set URL allowlist regex patterns. | `config.py` |
| `/config url_safety blocklist` | Set URL blocklist regex patterns. | `config.py` |
| `/config url_safety clear` | Clear URL allowlist or blocklist. | `config.py` |
| `/config url_safety view` | View URL safety settings. | `config.py` |

## Tools

| Command | Description | Source |
| --- | --- | --- |
| `/tools clear-guild-recency` | Clear the guild-wide short-term recency summary. | `tools_admin.py` |
| `/tools debug raw-capture-disable` | Disable temporary raw tool capture. | `tools_admin.py` |
| `/tools debug raw-capture-enable` | Temporarily enable raw tool capture for debugging. | `tools_admin.py` |
| `/tools debug raw-capture-status` | Show whether temporary raw capture is enabled. | `tools_admin.py` |
| `/tools inspect` | Inspect tool candidates, denied tools, and filtering reasons. | `tools_admin.py` |
| `/tools manage` | Open the Discord-native tool management panel. | `tools_admin.py` |
| `/tools mcp approve-global` | Approve a discovered admin-global MCP tool. | `tools_admin.py` |
| `/tools mcp approve-guild` | Approve a discovered guild-scoped MCP tool. | `tools_admin.py` |
| `/tools mcp discover-global` | Discover tools from an admin-global MCP server. | `tools_admin.py` |
| `/tools mcp discover-guild` | Discover tools from a guild-scoped MCP server. | `tools_admin.py` |
| `/tools mcp enable-global` | Enable or disable an admin-global MCP server. | `tools_admin.py` |
| `/tools mcp enable-guild` | Enable or disable a guild-scoped MCP server. | `tools_admin.py` |
| `/tools mcp health` | Show MCP discovery/call health and cooldown state. | `tools_admin.py` |
| `/tools mcp list-registrations` | List MCP registrations visible from this server. | `tools_admin.py` |
| `/tools mcp list-tools` | List discovered MCP tools for admin-global and this guild. | `tools_admin.py` |
| `/tools mcp register-global` | Register an admin-global MCP server. | `tools_admin.py` |
| `/tools mcp register-guild` | Register a guild-scoped MCP server. | `tools_admin.py` |
| `/tools mcp trust-global` | Set trust for an admin-global MCP server. | `tools_admin.py` |
| `/tools policy clear-category` | Clear guild policy for a tool category. | `tools_admin.py` |
| `/tools policy clear-tool` | Clear guild policy for a specific tool. | `tools_admin.py` |
| `/tools policy set-category` | Set guild policy for a tool category. | `tools_admin.py` |
| `/tools policy set-tool` | Set guild policy for a specific tool. | `tools_admin.py` |
| `/tools quarantine clear` | Clear quarantine state for a specific tool in this guild. | `tools_admin.py` |
| `/tools quarantine status` | Show active tool quarantine state for this guild. | `tools_admin.py` |
| `/tools refresh` | Clear short-term channel memory and set a new context boundary. | `tools_admin.py` |
| `/tools status` | Show tool availability for this server. | `tools_admin.py` |
