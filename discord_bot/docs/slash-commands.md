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
| `/welcome manage` | Open the feature-packed welcome admin panel for channel, text, welcome-image template/destination controls, DM settings, toggles, and test actions. | `config.py` |

## Config

| Command | Description | Source |
| --- | --- | --- |
| `/config ai manage` | Open the AI settings section of the config panel. | `config.py` |
| `/config auth` | Authenticate for sensitive config operations. | `config.py` |
| `/config custom_endpoint manage` | Open provider and custom endpoint settings in the config panel. | `config.py` |
| `/config env example` | Send the guild .env.example template. | `config.py` |
| `/config env upload` | Upload a .env file for this guild. | `config.py` |
| `/config keys manage` | Open provider, key, and model configuration in the config panel. | `config.py` |
| `/config model manage` | Open provider and model configuration in the config panel. | `config.py` |
| `/config panel` | Open the primary Discord-native config panel. | `config.py` |
| `/config password change` | Change the config password. | `config.py` |
| `/config password reset` | Reset the config password (owner only). | `config.py` |
| `/config password set` | Set the config password (first time only). | `config.py` |
| `/config toggle manage` | Open capability toggles, including evil mode, in the config panel. | `config.py` |
| `/config url_safety manage` | Open the URL safety section of the config panel. | `config.py` |

## Tools

| Command | Description | Source |
| --- | --- | --- |
| `/tools context clear-guild-recency` | Clear the guild-wide short-term recency summary. | `tools_admin.py` |
| `/tools context refresh` | Clear short-term channel memory and set a new context boundary. | `tools_admin.py` |
| `/tools debug raw-capture-disable` | Disable temporary raw tool capture. | `tools_admin.py` |
| `/tools debug raw-capture-enable` | Temporarily enable raw tool capture for debugging. | `tools_admin.py` |
| `/tools debug raw-capture-status` | Show whether temporary raw capture is enabled. | `tools_admin.py` |
| `/tools info inspect` | Inspect tool candidates, denied tools, and filtering reasons. | `tools_admin.py` |
| `/tools info status` | Show tool availability for this server. | `tools_admin.py` |
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
