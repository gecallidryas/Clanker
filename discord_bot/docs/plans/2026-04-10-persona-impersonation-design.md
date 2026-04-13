# Persona Impersonation Design

## Summary

Add a staff-only `/persona impersonate` slash command that analyzes a tagged user's recent server-visible messages, generates a custom persona that mirrors that user's speaking style, copies the user's avatar into persona assets, and saves the result as an inactive custom persona for later review and activation.

This feature should fit the existing custom persona architecture instead of introducing a separate runtime-only impersonation mode.

## Goals

- Let server staff generate a saved custom persona from a real member's recent message history.
- Use the guild's `GEMINI_PROFILE_KEY` path for style analysis and prompt generation.
- Persist the generated persona as a normal custom persona with editable prompt fields.
- Copy the target member's current Discord avatar into the custom persona asset store.
- Save persona-specific sample dialogue that the prompt builder can inject when that persona is active.

## Non-Goals

- Auto-activating the generated persona.
- Supporting personal opt-in or self-service generation in v1.
- Building a temporary impersonation mode that bypasses custom persona storage.
- Reusing or overwriting the guild-global `/teach sampledialogue` bank.
- Generating banners or cloning rich profile metadata beyond display name, avatar, and voice/style.

## User Flow

Command shape:

`/persona impersonate member:@user name:<optional custom name>`

Behavior:

1. Staff member runs the command in a guild.
2. The bot verifies `Manage Guild`.
3. The bot scans up to the last `1000` visible messages from the tagged member across readable guild text channels.
4. The bot filters low-signal lines such as commands, duplicates, empty messages, attachment-only posts, and trivial filler.
5. The bot requires at least `100` usable messages after filtering.
6. The bot sends a structured analysis prompt to the Gemini profile-text path.
7. Gemini returns a compact bio, a normal prompt, an optional evil prompt, aliases, and persona-specific sample dialogue lines.
8. The bot copies the target member avatar into the custom persona avatar directory.
9. The bot saves a regular custom persona row, including persona-specific sample dialogues.
10. The bot replies ephemerally with the saved persona name, message counts, and any fallbacks used.

The generated persona is not activated automatically. Staff can review or activate it later through the existing persona admin surface.

## Command Placement

The new command belongs in [`/mnt/e/femboibot/discord_bot/cogs/persona.py`](/mnt/e/femboibot/discord_bot/cogs/persona.py) under the existing `persona_group`.

This keeps all persona lifecycle actions in one cog:

- `/persona manage`
- `/persona edit`
- `/persona delete`
- `/persona impersonate`

## Architecture

### High-Level Approach

Use the existing custom persona storage flow as the source of truth and add a small impersonation pipeline helper module to keep the cog thin.

Recommended structure:

- [`/mnt/e/femboibot/discord_bot/cogs/persona.py`](/mnt/e/femboibot/discord_bot/cogs/persona.py): slash command, permission checks, interaction lifecycle, final persistence call.
- `discord_bot/utils/persona_impersonation.py`: message collection, filtering, prompt building, Gemini response parsing, avatar copy helper, naming collision helper.
- [`/mnt/e/femboibot/discord_bot/utils/db_handler.py`](/mnt/e/femboibot/discord_bot/utils/db_handler.py): schema migration and accessors for persona-specific sample dialogues.
- [`/mnt/e/femboibot/discord_bot/cogs/ai_brain.py`](/mnt/e/femboibot/discord_bot/cogs/ai_brain.py): prompt builder support for persona-specific sample dialogues when a custom persona is active.

### Message Collection

The collector scans readable guild text channels until it reaches either:

- `1000` raw messages from the target user, or
- the available accessible history is exhausted.

Rules:

- Skip bot authors.
- Skip messages without meaningful text content.
- Skip obvious slash/prefix commands.
- Skip repeated near-identical messages after normalization.
- Skip very short filler-only lines.
- Preserve punctuation, casing, emoji, and slang for kept lines because style fidelity depends on them.

The collector should return both:

- raw counts for user-facing status
- filtered samples for generation

### Prompt Generation

The generator should call `generate_guild_gemini_profile_text(...)` so it uses the guild's profile/summarization key path.

Prompt shape:

- Explain that the model is generating a Discord bot persona that should mirror communication style closely without claiming literal identity.
- Provide a filtered message corpus plus lightweight style statistics.
- Request structured JSON output with:
  - `bio`
  - `aliases`
  - `normal_prompt`
  - `evil_prompt`
  - `sample_dialogues`

The prompt should explicitly ask the model to capture:

- sentence length tendencies
- punctuation habits
- emoji usage
- slang/catchphrases
- formality level
- teasing vs. blunt vs. warm tone
- response patterns for casual chat, joking, affection, disagreement, and short acknowledgements

The prompt should also explicitly forbid:

- claiming to truly be the original user
- revealing hidden chain-of-thought
- inventing private facts not present in the corpus
- writing prompts that break moderation or tool rules

### Avatar Copy

The target member avatar should be copied from `member.display_avatar.read()` and saved into the existing custom avatar path convention under `DATA_DIR / "avatars" / "custom"`.

The saved filename should follow the existing persona asset format:

- `guild_<guild_id>_<slug>_avatar.webp`

If avatar read or conversion fails, the persona should still be created with `avatar_path=None` and the confirmation message should mention the fallback.

### Persistence

The generated persona should be saved through the existing `create_custom_persona(...)` path.

Reuse existing fields:

- `name`
- `mode_key`
- `bio`
- `avatar_path`
- `normal_prompt`
- `evil_prompt`
- `aliases`

Add one new field on `custom_personas`:

- `sample_dialogues_json TEXT`

This field stores a JSON array of strings or compact speaker/dialogue objects for persona-specific example lines. This keeps impersonation data attached to the persona instead of polluting the guild-global `sample_dialogues` table.

The generated bio should include a short provenance note, for example:

`Generated from @DisplayName message history on 2026-04-10.`

That note provides transparency without needing another metadata table in v1.

### Prompt Builder Integration

When a custom persona is active, the prompt builder should load persona-specific sample dialogues from the active persona row and inject them into the prompt before falling back to guild-global sample dialogues.

Recommended behavior:

- If the active custom persona has saved sample dialogues, use those for the `SAMPLE DIALOGUES` section.
- Otherwise keep current guild-global `get_sample_dialogues(...)` behavior.

This keeps generated impersonation voices self-contained and avoids cross-contaminating other personas or the default bot mode.

## Naming Rules

Default persona name:

- target member display name

Optional override:

- use `name` argument if supplied

Collision handling:

- if the chosen name already exists in the guild, generate a deterministic suffix such as `Name (impersonated)` and then `Name (impersonated 2)` as needed.

The command should never fail solely because of a simple name collision.

## Safety And Failure Handling

Safeguards:

- guild-only
- `Manage Guild` required
- no automatic activation
- minimum `100` usable filtered messages
- fail cleanly on Gemini errors
- soft fallback on avatar copy failure

Failure responses:

- not enough usable messages: ephemeral error with scanned and usable counts
- profile key missing: ephemeral error pointing staff to `GEMINI_PROFILE_KEY`
- Gemini returned invalid JSON or incomplete payload: ephemeral error, no persona saved
- avatar failure: persona saved without avatar, with fallback note
- database uniqueness collision after suffix attempts: ephemeral error, no partial success claim

## Testing Strategy

Add focused tests for:

- message filtering and deduplication
- minimum-message threshold behavior
- naming collision resolution
- Gemini JSON parsing and validation
- persona row persistence including `sample_dialogues_json`
- active custom persona prompt injection in `ai_brain`
- slash command permission denial and success path

## Why This Design

This design fits the current bot architecture because custom personas already own prompts, avatars, activation state, and admin UX. Adding `/persona impersonate` as a generator for those same records keeps the feature understandable for staff, keeps prompt behavior consistent, and avoids a separate impersonation subsystem that would be harder to review, test, and moderate.
