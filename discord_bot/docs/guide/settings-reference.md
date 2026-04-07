# Settings Reference

## Capabilities And Toggles

Owned primarily by:

- `discord_bot/cogs/config.py`
- `discord_bot/utils/tool_flags.py`
- `discord_bot/utils/tool_registry.py`
- `discord_bot/tools/availability.py`

Settings exposed through `/config toggle manage`:

- `web_search_enabled`: lets the bot use web search helpers where available.
- `image_gen_enabled`: enables image generation flows and related tool availability.
- `youtube_enabled`: allows YouTube processing features.
- `profile_peek_enabled`: allows profile picture analysis features.
- `rag_enabled`: enables local retrieval-augmented features.
- `sticker_usage_enabled`: allows sticker-based expression behavior.
- `emoji_usage_enabled`: allows emoji-heavy expression behavior.
- `gif_responses_enabled`: enables GIF reply behavior.
- `pin_message_enabled`: enables pin-message behavior.
- `self_teaching_enabled`: enables self-teaching and persistent learning behaviors.
- `url_safety_enabled`: turns URL safety moderation on or off.
- `evil mode`: server-level persona behavior toggle backed by `get_evil_mode` and `set_evil_mode` in `discord_bot/utils/db_handler.py`.

## AI Behavior

Owned primarily by:

- `discord_bot/cogs/config.py`
- `discord_bot/utils/guild_ai.py`
- `discord_bot/utils/streaming/`
- `discord_bot/utils/persona_queue.py`

Settings exposed through `/config ai manage`:

- reply cooldown seconds
- reply cooldown scope
- self-reply limit
- auto-channel threshold
- AI channel whitelist
- AI auto-response channels
- streaming enabled and stream budget values
- thought log level
- thought log channel
- mod-log fallback reuse for thought logging

Auto-reply behavior notes:

- direct mentions, reply-to-bot chains, and persona trigger words still act as deterministic triggers
- auto-response channels are candidate zones for conservative no-mention replies, not unconditional response channels
- auto-channel threshold `0` means always eligible for evaluation, not always reply
- users can separately opt out of passive no-mention auto-replies through `/personal privacy` without opting out of personal memory
- streamed reply concurrency is per `(channel, user)`, not one active stream for the whole channel
- same-user explicit trigger fragments are coalesced for a short fixed debounce window before prompt execution
- if the same user adds more text before any visible streamed output appears, the bot restarts that in-flight turn with the merged content
- if visible output has already started, extra same-user fragments collapse into one buffered follow-up turn after the current same-user turn finishes, including any queued persona replies

## Providers, Keys, Models, And Custom Endpoint

Owned primarily by:

- `discord_bot/cogs/config.py`
- `discord_bot/utils/guild_ai.py`
- `discord_bot/utils/image_generation.py`
- `discord_bot/utils/api_manager.py`
- `discord_bot/utils/db_handler.py`

Settings exposed through `/config keys manage`, `/config model manage`, and `/config custom_endpoint manage`:

- Gemini API key pools for general, translate, summarize, and profile use
- OpenRouter API key pools
- Gemini model selections
- OpenRouter model selection and fallback models
- image provider and image model values loaded from env upload
- custom endpoint URL
- custom endpoint API key
- custom model name
- custom model capabilities
- custom endpoint enabled flag

### Database Summarization Caveat

Stored-memory reconciliation is separate from the public `/tldr` conversation summarizer.

Owned primarily by:

- `discord_bot/cogs/memories.py`
- `discord_bot/cogs/teach.py`
- `discord_bot/utils/database_summarizer.py`
- `discord_bot/utils/api_manager.py`

Behavior:

- `/remember personal` and `/remember server` may reconcile existing stored facts with a new fact before saving.
- `/teach attribute` may reconcile persona attributes before replacing the stored set.
- `/teach sampledialogue` may reconcile stored sample lines before replacing the stored set.

Current runtime dependency:

- `DatabaseSummarizer` uses `get_gemini_summarize_manager()` from `discord_bot/utils/api_manager.py`.
- That manager is backed by the process environment variable `GEMINI_SUMMARIZE_KEY`.
- It also requires the `google-genai` package to be installed in the running bot environment.

Important limitation:

- This reconciler does not currently read guild-uploaded summarize keys from guild config.
- If `GEMINI_SUMMARIZE_KEY` is missing or `google-genai` is unavailable, the reconciler disables itself and the bot falls back to storing the new fact or teaching entry directly without AI reconciliation.

## URL Safety

Owned primarily by:

- `discord_bot/cogs/config.py`
- `discord_bot/utils/db_handler.py`

Settings exposed through `/config url_safety manage`:

- action: `warn` or `delete`
- allowlist regex patterns
- blocklist regex patterns

## Welcome, Autorole, Staff, And Mod Log

Owned primarily by:

- `discord_bot/cogs/config.py`
- `discord_bot/cogs/social.py`
- `discord_bot/utils/db_handler.py`

Settings exposed through `/welcome manage`, `/autorole manage`, `/staff manage`, and `/modlog manage`:

- welcome enabled state
- welcome channel
- welcome message template
- DM welcome message and DM toggle
- autorole enabled state
- autorole role ID
- bot staff roles and levels
- moderation log channel

## Env Upload

Owned primarily by:

- `discord_bot/cogs/config.py`
- `discord_bot/guild.env.example`

`/config env upload` is the bulk-import path for provider and model configuration. It validates the uploaded keys, normalizes model names, encrypts secrets where needed, and stores the resulting values in guild config.
