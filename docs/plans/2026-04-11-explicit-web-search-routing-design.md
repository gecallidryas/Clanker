# Explicit Web Search Routing Design

**Date:** 2026-04-11

**Goal:** Ensure explicit search requests such as "search web", "google", and "web search" always execute a real web search using configured Gemini capabilities first, then Brave when available, and return linked sources instead of a plain summary.

## Problem

The current bot has a `web_search` tool with Brave and DuckDuckGo backends, but it depends on the model deciding to call that tool. That breaks the intended UX in two cases:

- some configured models cannot issue tool calls at all
- even when the tool is called, the returned text is a plain `title - url (snippet)` summary instead of clickable source links

That means an explicit user instruction to search the web can silently degrade into a normal model answer or a flattened summary, which is not acceptable for this feature.

## Approved Direction

Add an explicit search-intent routing path in `discord_bot/cogs/ai_brain.py` that runs before normal model response generation. When the incoming message clearly asks to search the web, the bot should execute the search itself and reply with search results formatted as Discord markdown links using `[source title](source url)`.

Provider priority should be:

1. configured Gemini-backed web search when available for the guild
2. Brave Search when a Brave API key exists
3. existing non-Gemini fallback only as a last-resort compatibility path

The user-facing response should present results directly, not collapse them into a prose summary.

## Scope

- detect explicit web-search commands in user messages
- bypass model tool-call dependence for those requests
- prefer configured Gemini web search
- fall back to Brave when Gemini web search is unavailable
- format each result as a markdown hyperlink line with source title and URL
- preserve snippets in a readable per-result layout
- add regression tests for provider selection, formatting, and explicit routing

## Out of Scope

- changing general factual-answer behavior for non-explicit search requests
- rewriting the whole tool system or transport stack
- changing unrelated prompt instructions for the rest of the bot

## Architecture

### Explicit Search Detection

`discord_bot/cogs/ai_brain.py` should gain a small detector for high-confidence explicit search phrases such as:

- `search web`
- `web search`
- `google`
- `look this up`
- similar imperative phrasing

This detector should be conservative. It should only trigger for clear search intent, not any generic factual question.

### Search Execution Layer

`discord_bot/utils/web_search.py` should become the authoritative executor for explicit search requests. It should expose a provider-selection path that:

- checks for configured Gemini API capability first
- uses Gemini-backed web search when available
- otherwise checks for a Brave API key
- falls back to the existing DuckDuckGo path only when neither higher-priority provider is available

The returned tool data should preserve:

- `provider`
- `query`
- normalized `results`
- user-facing `formatted` text

### Result Formatting

The formatter should stop producing `title - url (snippet)` output. Instead it should emit one result at a time using markdown links:

- `[Source Name](https://example.com)`
- snippet on the next line if present

This keeps the result list readable and clickable in Discord.

### AI Brain Integration

When explicit search intent is detected, `AIBrain` should:

- build the normal tool context
- call the `web_search` execution path directly
- send the formatted result message to the channel
- skip the normal model-generation path for that turn

This guarantees correct behavior even when the active model does not support tools.

## Testing Strategy

Add focused regression coverage for:

- provider selection preferring Gemini over Brave
- Brave selection when Gemini search is unavailable
- fallback behavior when only the legacy provider is available
- markdown hyperlink formatting
- explicit routing in `AIBrain` for a message like `search web cats`

The tests should verify real returned strings rather than only asserting that some formatted field exists.

## Risks And Mitigations

- false positives on casual messages
  - keep the detector conservative and test only clear imperative phrases
- provider capability ambiguity for Gemini
  - detect from configured guild model/key availability in one helper instead of scattering checks
- result formatting regressions
  - lock down exact hyperlink output in tests

## Decision

Implement explicit search-intent interception in `AIBrain`, centralize provider priority in `web_search`, and return direct markdown-linked sources per result so explicit web-search requests behave consistently across models and providers.
