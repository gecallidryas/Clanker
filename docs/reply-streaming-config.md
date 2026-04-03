# Reply Streaming Config

The reply-streaming overhaul adds guild config controls under `/config ai`:

- `/config ai view`
  Shows reply gating, streaming budget, and thought-log settings.

- `/config ai streaming on|off`
  Enables or disables streamed mention/reply responses. One-shot generation remains available as the fallback path.

- `/config ai stream_budget <min_flush_chars> <stall_seconds> <min_interval_seconds> <max_messages> <max_total_chars>`
  Tunes how aggressively streamed replies flush visible text and how much Discord output is allowed per turn.

- `/config ai thought_channel [channel]`
  Sets or clears the dedicated thought/debug channel.

- `/config ai thought_level off|summary|raw_debug`
  Controls whether the bot posts summary-only or raw provider debug/thought output when available.

- `/config ai thought_modlog on|off`
  Allows or denies fallback reuse of the configured mod-log channel for thought/debug posts when no dedicated thought channel is set.

Custom endpoints still use `/config custom_endpoint set`, but streaming/tool behavior now depends on explicit capability flags:

- `openai_compat`
- `streaming`
- `tools`
- `vision`
- `video`

Without explicit OpenAI-compat capability flags, custom endpoints are treated as best-effort text-only endpoints.
