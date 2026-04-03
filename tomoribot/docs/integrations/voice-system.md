# Voice System

TomoriBot has a bidirectional voice pipeline: inbound **STT** (users speak → bot reads) and outbound **TTS** (bot speaks → users hear). Both sides are currently powered by ElevenLabs, but the architecture is intentionally service-agnostic so future providers (Whisper STT, Qwen TTS, local services) can be dropped in.

---

## Architecture Overview

```
                 ┌───────────────────────────────────────────────────────┐
                 │                   INBOUND (STT)                       │
                 │  User voice message ──► download ──► STT API          │
                 │                                        │               │
                 │                         transcript injected into       │
                 │                         context as [System: ...]       │
                 └───────────────────────────────────────────────────────┘

                 ┌───────────────────────────────────────────────────────┐
                 │                   OUTBOUND (TTS)                      │
                 │  LLM calls generate_voice_message tool                │
                 │       │                                               │
                 │       ▼                                               │
                 │  TTS API ──► audio buffer                             │
                 │       │                                               │
                 │       ├──► waveform generation (ffmpeg)               │
                 │       │         │                                     │
                 │       │    native Discord voice message               │
                 │       │    (raw REST, bypasses discord.js)            │
                 │       │                                               │
                 │       └──► fallback: plain attachment                 │
                 └───────────────────────────────────────────────────────┘

                 ┌───────────────────────────────────────────────────────┐
                 │              SHARED: Transcript Cache                 │
                 │  voiceTranscriptCache  (in-memory TTL, default 2h)    │
                 │  key: Discord message ID                              │
                 │  source: "user_stt" | "tts"                           │
                 └───────────────────────────────────────────────────────┘
```

---

## Permission Model

Voice features require all three gates to be open:

| Gate | Where set | Default |
|------|-----------|---------|
| Server opt-in key (`elevenlabs`) | `/optionalkey elevenlabs set` | none (feature disabled) |
| Per-persona voice assignment | `/config voice elevenlabs` | none (TTS disabled per persona) |
| Server-level permission flag (`voice_message_enabled`) | `/config permissions` (checkbox) | `true` |

The `generate_voice_message` tool is excluded from the tool list in `toolRegistry.ts` unless all three are satisfied. The permission flag exists so admins with a key can still opt out server-wide without removing the key.

---

## Inbound: Speech-to-Text (STT)

### Flow

1. **Trigger detection** — `messageCreate` event handler detects an audio attachment via `isAudioAttachment()` (checks MIME type prefix `audio/` or known extension).
2. **Transcription** — `transcribeMessageAudioAttachment()` in `audioAttachmentTranscription.ts`:
   - Looks up the server's ElevenLabs opt key.
   - Downloads the audio via `safeDownload()` (size-capped, timeout-guarded).
   - Calls `transcribeWithElevenLabs()` → `POST /v1/speech-to-text`.
3. **Cache** — successful transcript stored in `voiceTranscriptCache` as `user_stt`.
4. **Context injection** — history formatter inlines the cached transcript as `[System: Voice message transcript: ...]` so the LLM reads it as plain text.

### Supported formats

AAC, FLAC, M4A, MP3, MP4, MPEG, MPGA, OGA, OGG, Opus, WAV, WebM (limited by ElevenLabs STT API).

### Key files

| File | Purpose |
|------|---------|
| `src/utils/audio/audioAttachmentTranscription.ts` | Entry point — attachment detection + orchestration |
| `src/utils/audio/elevenLabsStt.ts` | ElevenLabs STT API wrapper |
| `src/utils/audio/voiceTranscriptCache.ts` | In-memory transcript TTL cache |

---

## Outbound: Text-to-Speech (TTS)

### Flow

1. **LLM decides to speak** — calls the `generate_voice_message` tool (`GenerateVoiceMessageTool`) with a `title` and `script`.
2. **Expression tag processing** — `sanitizeElevenLabsTaggedScript()` normalizes the script and produces two versions:
   - `rawScript` — sent to the TTS API, includes `[expression tags]` like `[happy]`, `[whispers]`
   - `captionText` — tags stripped, stored in cache for history display
3. **Synthesis** — `synthesizeSpeechWithElevenLabs()` → `POST /v1/text-to-speech/{voiceId}` → returns an audio buffer.
4. **Waveform generation** — `generateVoiceMessageMetadata()` uses `music-metadata` (pure JS, parses header for duration) and `ffmpeg-static` (decodes to raw PCM, computes 100 amplitude samples).
5. **Send as native Discord voice message** — if waveform succeeds, sends via raw REST with `flags: 8192 (IS_VOICE_MESSAGE)` and `waveform` + `duration_secs` on the attachment. Two sub-paths:
   - **Webhook path** (alter persona with token) — `sendNativeVoiceMessageViaRest()` posts to the webhook endpoint.
   - **Bot identity path** (main persona or no webhook token) — `sendNativeVoiceMessageViaBotRest()` uses `client.rest.post()` with `passThroughBody: true`.
6. **Fallback** — if waveform generation fails or both REST paths fail, falls back to a plain `AttachmentBuilder` send (no native voice UI).
7. **Cache** — `sentMessageId` + `captionText` stored in `voiceTranscriptCache` as `tts`.

### Why raw REST?

discord.js `MessagePayload` serialization silently drops unknown fields from attachment objects. The Discord API requires `waveform` and `duration_secs` to render the native voice message waveform UI — these are non-standard fields not in the discord.js type model, so the library strips them. The raw REST path builds a `multipart/form-data` body directly to preserve these fields.

### Expression tags

ElevenLabs v3 models (`eleven_v3`) support inline delivery cues in brackets:
- **Emotional states**: `[happy]`, `[sad]`, `[tired]`, `[nervous]`, `[excited]`
- **Actions**: `[whispers]`, `[laughs]`, `[sighs softly]`, `[clears throat]`

Tags matching `[A-Za-z][A-Za-z0-9 _-]{0,30}]` are passed through to the API. When `ELEVENLABS_TTS_STRIP_UNSUPPORTED_TAGS=true`, brackets that don't match this pattern are removed before sending. Either way, all tags are stripped from `captionText` so history shows clean text.

### Voice assignment

Each persona has its own `elevenlabs_voice_id` and `elevenlabs_voice_name` columns (on the `tomoris` table). Assignment is done via `/config voice elevenlabs`:
1. Fetches available voices from `/v1/voices` (sorted alphabetically).
2. Server manager picks a persona via paginated button UI.
3. Picks a voice via a paginated modal select.
4. Writes `elevenlabs_voice_id` + `elevenlabs_voice_name` to the persona row.

### Key files

| File | Purpose |
|------|---------|
| `src/tools/functionCalls/generateVoiceMessageTool.ts` | Tool implementation, send paths, fallback |
| `src/utils/audio/elevenLabsTts.ts` | ElevenLabs TTS API wrapper |
| `src/utils/audio/voiceMessageMetadata.ts` | Waveform + duration generation via ffmpeg |
| `src/utils/audio/elevenLabsVoiceCatalog.ts` | Voice catalog fetch from `/v1/voices` |
| `src/commands/config/voice/elevenlabs.ts` | `/config voice elevenlabs` command |

---

## Shared: Transcript Cache

`src/utils/audio/voiceTranscriptCache.ts` — in-memory `Map<messageId, entry>` with TTL eviction.

| Field | Description |
|-------|-------------|
| `transcript` | Clean text (no expression tags, no system prefix) |
| `source` | `"user_stt"` (inbound) or `"tts"` (outbound) |
| TTL | `VOICE_TRANSCRIPT_CACHE_TTL_MINUTES` (default: 120 min) |

On cache miss, history formatting falls back to `[Attachment: filename.mp3]`. The current-turn user message is always re-transcribed fresh — the cache only speeds up older history entries.

---

## Shared config: `elevenLabsShared.ts`

All ElevenLabs constants and config helpers live here. Env vars (all optional, defaults shown):

| Env var | Default | Purpose |
|---------|---------|---------|
| `ELEVENLABS_TTS_MODEL_ID` | `eleven_v3` | TTS model |
| `ELEVENLABS_TTS_TIMEOUT_MS` | `20000` | TTS request timeout |
| `ELEVENLABS_TTS_MAX_CHARS` | `2000` | Max script length before truncation |
| `ELEVENLABS_TTS_OUTPUT_FORMAT` | `mp3_44100_128` | Audio format sent to Discord |
| `ELEVENLABS_TTS_STRIP_UNSUPPORTED_TAGS` | `false` | Strip non-standard bracket tags |
| `ELEVENLABS_STT_MODEL_ID` | `scribe_v2` | STT model |
| `ELEVENLABS_STT_TIMEOUT_MS` | `20000` | STT request timeout |
| `ELEVENLABS_STT_MAX_SIZE_MB` | `20` | Max audio file size for transcription |
| `ELEVENLABS_STT_MAX_TRANSCRIPT_CHARS` | `1500` | Max transcript length after normalization |
| `VOICE_WAVEFORM_TIMEOUT_MS` | `5000` | ffmpeg waveform generation timeout |
| `VOICE_TRANSCRIPT_CACHE_TTL_MINUTES` | `120` | Voice transcript cache expiry |

---

## Adding a New Voice Provider

The current implementation couples the service calls to ElevenLabs directly. Future providers should follow this pattern:

### For a new STT provider (e.g. Whisper, Qwen ASR)

1. Create `src/utils/audio/{providerName}Stt.ts` with a function matching this signature:
   ```ts
   transcribeWith{Provider}(request: {Provider}SttRequest): Promise<{Provider}SttResult>
   // result must include: success, transcriptText?, errorKind?, details?
   ```
2. Update `audioAttachmentTranscription.ts` to call the new provider (or add a routing layer if multiple STT providers should coexist).
3. Add an opt key lookup for the new provider's API key using the existing `hasOptApiKey` / `getOptApiKey` pattern in `src/utils/security/crypto.ts`.
4. Add an `/optionalkey {provider} set/remove` command pair.

### For a new TTS provider (e.g. Qwen TTS, local Kokoro)

1. Create `src/utils/audio/{providerName}Tts.ts` with a function matching:
   ```ts
   synthesizeSpeechWith{Provider}(request): Promise<{
     success: boolean;
     audioBuffer?: Buffer;
     contentType?: string;
     extension?: string;
     cleanedCaptionText?: string;
   }>
   ```
2. The waveform generation step (`generateVoiceMessageMetadata`) and the two send paths in `GenerateVoiceMessageTool` are provider-agnostic — only the synthesis call needs to change.
3. Add a per-persona voice assignment command under `src/commands/config/voice/{provider}.ts`.
4. Store the voice identifier on the `tomoris` row (add columns as needed with a migration script).
5. Update `toolRegistry.ts` to check for the new provider's opt key and voice assignment before exposing the tool.

### Key constraints regardless of provider

- The send path **must** use raw REST (not `interaction.reply` or `channel.send` with files) to preserve `waveform` + `duration_secs` for the native Discord voice UI.
- Always store the caption text in `voiceTranscriptCache` as `"tts"` so history formatting can reconstruct what was said.
- Expression tag handling is ElevenLabs-specific — new providers may have different prosody markup and should implement their own sanitization layer.
