# 6. Event System

TomoriBot routes Discord events through one dispatcher: `src/handlers/eventHandler.ts`.

## Dispatcher Model

- `eventFolderMap` maps Discord event names -> folder names under `src/events/`.
- All files in the mapped folder are executed in lexical order.
- Multiple Discord events can map to one folder (emoji/sticker fan-in).

## Current Event Folders

- `clientReady`
- `guildCreate`
- `guildEmojisUpdate`
- `guildMemberAdd`
- `guildStickersUpdate`
- `interactionCreate`
- `messageCreate`
- `rateLimit`

## Current Important Mappings

- `messageCreate` -> `messageCreate`
- `interactionCreate` -> `interactionCreate`
- `clientReady` -> `clientReady`
- `guildCreate` -> `guildCreate`
- `guildMemberAdd` -> `guildMemberAdd`
- `emojiCreate`/`emojiDelete`/`emojiUpdate` -> `guildEmojisUpdate`
- `stickerCreate`/`stickerDelete`/`stickerUpdate` -> `guildStickersUpdate`
- `rateLimit` -> `rateLimit`

`voiceStateUpdate` and `presenceUpdate` are also mapped by the dispatcher, but no active handler folders are currently present, so those mappings no-op.

## Typical Flows

### Message event

`messageCreate` -> `events/messageCreate/*.ts` -> chat/context/tool/stream pipeline.

Current message preprocessing in `tomoriChat.ts` enriches fetched history before `buildContext()`:
- reply-reference system annotations (message ID + quoted content)
- media extraction and media-source message IDs
- reaction context annotations (emoji/counts plus budgeted reactor identity fetches with counts-only fallback)

### Slash command event

`interactionCreate` -> `events/interactionCreate/handleCommands.ts` -> command lookup and execution.

### Ready event

`clientReady` handlers run startup tasks such as command registration and MCP registration.

### Member join event

`guildMemberAdd` -> `events/guildMemberAdd/newUser.ts`

- registers the joining Discord user in the database
- optionally triggers a configured welcome message in the server's welcome channel
- welcome greetings reuse the normal `tomoriChat.ts` manual-trigger pipeline, including persona selection, queueing, and mention fallback checks

## Adding a New Event Handler

1. Create `src/events/{folderName}/`.
2. Add a default-export handler file.
3. Add/update mapping in `eventFolderMap`.
4. Restart and verify logs.
