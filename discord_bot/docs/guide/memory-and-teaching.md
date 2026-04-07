# Memory And Teaching Guide

This guide explains the difference between `remember` commands and `teach` commands.

## Quick Rule

- Use `remember` for durable facts the bot should know.
- Use `teach` for shaping how the bot speaks or for uploading retrievable documents.

## Remember Commands

### `/remember personal`

Stores a durable fact about a specific user in the current server.

Examples:

- `/remember personal fact: I prefer they/them pronouns`
- `/remember personal fact: My timezone is Asia/Dhaka`
- `/remember personal fact: I like matcha and rhythm games`

Use this when the bot should remember something *about a person*.

### `/remember server`

Stores a durable fact about the server itself.

Examples:

- `/remember server fact: Spoilers belong in #spoilers`
- `/remember server fact: This server is mainly for anime roleplay`
- `/remember server fact: Partnership requests should ping moderators`

Use this when the bot should remember something *about the guild's norms, lore, or setup*.

## Teach Commands

### `/teach attribute`

Teaches high-level persona/style attributes that influence how the bot replies.

Examples:

- `/teach attribute attribute: Tone value: Warm, confident, older-sister energy`
- `/teach attribute attribute: Boundaries value: Supportive but not clingy`
- `/teach attribute attribute: Humor value: Gentle teasing, never cruel`

Use this for persistent behavioral guidance.

### `/teach sampledialogue`

Teaches example lines so the bot can mimic a desired reply style.

Examples:

- `/teach sampledialogue speaker: Oneesan dialogue: Ara ara, slow down and tell me what happened first.`
- `/teach sampledialogue speaker: Oneesan dialogue: Good work. Come here, you deserve a little praise.`
- `/teach sampledialogue speaker: Oneesan dialogue: If you're overwhelmed, we'll break it into one small step at a time.`

Use this when you want to show the bot what "good replies" sound like.

Important: in the current implementation, sample dialogues are guild-scoped, not tied to one specific persona record. If Oneesan is active, those examples can shape Oneesan's replies, but the same taught dialogue context is also available to other personas in that server.

### `/teach document`

Uploads a text, markdown, or PDF document for RAG/document retrieval.

Examples:

- community rules
- lore docs
- onboarding notes
- FAQ/reference material

Use this when the bot should be able to retrieve details from a longer document instead of remembering a short fact.

## Privacy Command

### `/personal privacy`

Lets a user opt out of personal memory in the current server.

Use `on` to opt out and `off` to opt back in.

## Which One Should I Use?

- "Remember that I like concise replies" -> `/remember personal`
- "Remember that this server uses #introductions for first messages" -> `/remember server`
- "Reply more like a caring older sister" -> `/teach attribute`
- "Reply with examples like these Oneesan lines" -> `/teach sampledialogue`
- "Read from this rules PDF when relevant" -> `/teach document`

## Current Implementation Notes

- `remember` is for fact storage.
- `teach attribute` and `teach sampledialogue` are currently guild-scoped training inputs.
- `teach document` is for RAG-backed retrieval, not short factual memory.
