# 7. Command System

TomoriBot uses Discord slash commands loaded dynamically from `src/commands/`.

## Loader and Execution Pipeline

- Registration/building: `src/utils/discord/commandLoader.ts`
- Runtime dispatch: `src/events/interactionCreate/handleCommands.ts`

Flow:

1. `loadCommandData()` scans command folders.
2. Command metadata is built into `SlashCommandBuilder` trees.
3. `handleCommands.ts` resolves category + group + subcommand.
4. Category cooldown is checked/set in `cooldowns` table (`COMMAND_CATEGORY`).
5. Target `execute()` is called with `(client, interaction, userData, locale)`.

## Command File Contract

Each command module exports:

- `configureSubcommand(subcommand)`
- `execute(client, interaction, userData, locale)`

Grouped commands are represented by folders:

- `src/commands/config/model/text.ts` -> `/config model text`

## Current Top-Level Categories

- `bot`
- `config`
- `contribute`
- `data`
- `donate`
- `forget`
- `generate`
- `help`
- `legal`
- `novelai`
- `persona`
- `personal`
- `reward`
- `server`
- `support`
- `teach`
- `tool`

## Category Restrictions

Defined in `commandLoader.ts`:

- Guild-only categories: `server`
- Manage Guild required by default: `config`, `server`

## Localization Strategy for Command Metadata

Do not hardcode descriptions/choice names.
Use `localizer("en-US", key)` in command builders.

`commandLoader.ts` then auto-applies locale localizations for other loaded locales.

Key pattern:

- Subcommand description: `commands.{category}.{path}.description`
- Option description: `commands.{category}.{path}.{option}_description`
- Choice name: `commands.{category}.{path}.{option}_choice_{value}`

Example path:

- file: `src/commands/forget/memory/personal.ts`
- command path: `forget.memory.personal`

## Interaction Timing Rules (Important)

Discord requires interaction acknowledgement within ~3 seconds.

### 3-Second Rule

On slash command invoke, acknowledge within 3 seconds using one of:

- `interaction.reply(...)`
- `interaction.deferReply(...)`
- `interaction.showModal(...)` (or modal helper that sends modal response)

After acknowledgement, you have up to ~15 minutes to complete.

### Pattern 1: Simple Command (No Deferral)

Use when work is synchronous/very fast and has no DB/API/file latency before response.

```ts
export async function execute(...) {
	if (!interaction.guild) {
		await replyInfoEmbed(...);
		return;
	}

	await interaction.reply({ content: "..." });
}
```

Rules:

- no DB query before first reply
- no external API call before first reply
- no filesystem work before first reply

### Pattern 2: Async Command (Defer First)

Use when any meaningful async work happens before first response.

```ts
export async function execute(...) {
	if (!interaction.guild) {
		await replyInfoEmbed(...);
		return;
	}

	await interaction.deferReply({ flags: MessageFlags.Ephemeral });

	const state = await getCachedTomoriState(interaction.guild.id);
	await sql`UPDATE ...`;

	await replyInfoEmbed(interaction, locale, { ... });
}
```

Rules:

- run fast validation first
- then defer before DB/API work
- do not defer at function start if early-return validation can finish immediately
- `/tool estimate cost` follows this pattern: it defers first, then fetches recent messages, builds context, and performs provider API token counting

### Pattern 3: Modal Command (No Initial Deferral)

Use when opening a modal for user input.

```ts
const modalResult = await promptWithRawModal(
	interaction,
	locale,
	{ ... },
	MessageFlags.Ephemeral, // auto-defer modal submission
);

if (modalResult.outcome !== "submit") return;
await sql`UPDATE ...`;
await replyInfoEmbed(modalResult.interaction, locale, { ... });
```

Rules:

- do not call `deferReply()` before showing modal
- pre-modal data loading must stay within the initial 3-second window
- if modal submit processing is async, pass `MessageFlags.Ephemeral` as `promptWithRawModal` arg 4

### Pattern 3A: Bulk Management Modal (Checkbox Groups)

Use when the user is managing an existing set of configured entries and batch keep/remove is better UX than a one-at-a-time select.

Examples:

- `/server whitelist remove`
- `/config remove modeloverride` (channels + personas together)

Rules:

- use `promptWithRawModal(...)` with checkbox groups and `MessageFlags.Ephemeral` auto-defer on submit
- pre-check every existing entry; unchecked means "remove" or "disable"
- set `minValues: 0` and `required: false` so users can uncheck everything
- chunk long lists into groups of 10 options; Discord allows at most 5 groups per modal (50 total options)
- if you are managing multiple entity types in one modal, keep them in separate checkbox groups by type
- if the total set exceeds 50 options, show an explicit overflow warning or route the user to a different bulk action
- after submit, diff original entries against submitted checked values, then invalidate caches only after successful DB writes

### Pattern 4: Pagination Helpers (No Pre-Defer)

Use when calling `replyPaginatedChoices(...)` or `promptWithPaginatedModal(...)`.

```ts
const result = await replyPaginatedChoices(interaction, locale, { ... });
```

```ts
const modalResult = await promptWithPaginatedModal(interaction, locale, { ... });
if (modalResult.outcome !== "submit") return;

// If submission handling is heavy, defer the modal submission immediately.
await modalResult.interaction.deferReply({ flags: MessageFlags.Ephemeral });
await sql`UPDATE ...`;
await replyInfoEmbed(modalResult.interaction, locale, { ... });
```

Rules:

- do not defer before pagination helpers (they acknowledge directly)
- keep pre-helper work under 3 seconds
- `promptWithPaginatedModal(...)` does not expose an auto-defer parameter; defer on submission manually when needed

### Pattern 5: Manual Deferral Timing

Use when you must delay deferral until after quick checks.

```ts
if (!hasPermission) {
	await replyInfoEmbed(...);
	return;
}

await interaction.deferReply({ flags: MessageFlags.Ephemeral });
const data = await exportServerData(...);
await interaction.editReply({ files: [data] });
```

Rules:

- keep pre-defer path fast
- once async heavy work starts, interaction must already be acknowledged

### Common Mistakes

- defer before `promptWithRawModal(...)` (causes already-acknowledged errors)
- no defer before DB/API updates in async command paths
- pre-defer before pagination helpers
- forgetting to defer modal submissions that do heavy async processing

### Helper Behavior Notes

- `replyInfoEmbed(...)` / `replySummaryEmbed(...)`:
  - handle `reply` vs `editReply` based on interaction state
- `promptWithRawModal(...)`:
  - shows modal (acknowledges original interaction)
  - optional arg 4 (`autoDeferReply`) can defer modal submission automatically
- `replyPaginatedChoices(...)` / `promptWithPaginatedModal(...)`:
  - send pagination UI immediately (acknowledges interaction)
  - should be called without pre-deferring

### Quick Reference

| Command Type | Defer Before Work? | Primary API |
| --- | --- | --- |
| Simple/Fast | No | `interaction.reply(...)` |
| DB/API before response | Yes | `interaction.deferReply(...)` then helper reply |
| Modal | No (before modal) | `promptWithRawModal(...)` |
| Pagination | No (before helper) | `replyPaginatedChoices(...)` / `promptWithPaginatedModal(...)` |
| Manual timing | Depends | defer after quick checks, before heavy work |

## Representative Command Groups

- `bot`: respond, generate(image), kill, impersonate
- `config`: setup, model(text/image/embedding), apikey(set/delete/rotation), sysprompt(change/clear/preset), params(*), timezone, maxmsgfetch, permissions, uncensors
- `server`: trigger(add/delete), whitelist(channel/role/remove), cooldown(triggers), autotrigger(*), matrix(link/unlink), quota(imagegen/textgen/reset), rpchannel(add/remove), welcomechannel
- `persona`: create, generate, import, export, default, swap, remove
- `tool`: ping, status, refresh, compact, comment

`/server autotrigger` is channel-scoped and uses one shared cycle across its configured channels. Threshold `0` enables always-reply in those channels. Positive values use either a fixed trigger (`min = max`) or a shared inclusive random range (`min-max`), rerolling after each successful auto-trigger. Removing a channel disables auto-trigger behavior for that channel.

`/bot generate image` is a modal-driven, fire-and-forget scene snapshot command. It plans against the current channel context with the active text provider, then renders with either the current provider's native image path or NovelAI's tag-based image tool when a NovelAI backend is available.

## Adding a New Command

1. Add a `.ts` file under the correct command category/group path.
2. Export `configureSubcommand` and `execute`.
3. Add locale keys in `src/locales/en-US.ts` and `src/locales/ja.ts`.
4. Run:
   - `bun run check-locales`
   - `bun run check`
   - `bun run lint`
