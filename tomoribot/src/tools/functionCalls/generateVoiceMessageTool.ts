import { AttachmentBuilder, Routes } from "discord.js";
import type { Webhook } from "discord.js";
import {
	BaseTool,
	type ToolContext,
	type ToolParameterSchema,
	type ToolResult,
} from "@/types/tool/interfaces";
import { synthesizeSpeechWithElevenLabs } from "@/utils/audio/elevenLabsTts";
import { ELEVENLABS_SERVICE_NAME } from "@/utils/audio/elevenLabsAccount";
import { setCachedVoiceTranscript } from "@/utils/audio/voiceTranscriptCache";
import { generateVoiceMessageMetadata } from "@/utils/audio/voiceMessageMetadata";
import type { VoiceMessageMetadata } from "@/utils/audio/voiceMessageMetadata";
import { getOptApiKey } from "@/utils/security/crypto";
import { sendWebhookMessageWithIdentity } from "@/utils/discord/webhookManager";
import { log } from "@/utils/misc/logger";

/** Discord IS_VOICE_MESSAGE flag value (1 << 13). */
const IS_VOICE_MESSAGE_FLAG = 8192;

/** Discord REST API base URL. */
const DISCORD_API_BASE = "https://discord.com/api/v10";

export class GenerateVoiceMessageTool extends BaseTool {
	name = "generate_voice_message";
	description =
		"Generate a spoken Discord audio message using the active persona's configured ElevenLabs voice. Use this only when voice delivery materially improves the reply. You may include bracketed expression tags anywhere in the script to shape delivery — both emotional states (e.g. [happy], [sad], [tired], [nervous]) and actions (e.g. [whispers], [laughs], [sighs softly]) are supported. Use them when they naturally fit the character and tone. The tool sends the audio attachment directly to the channel with no text caption.";
	category = "discord" as const;

	parameters: ToolParameterSchema = {
		type: "object",
		properties: {
			title: {
				type: "string",
				description:
					"A short descriptive title for the voice message (e.g. \"greeting\", \"farewell\", \"apology\"). Used as the audio filename. Keep it lowercase with no spaces.",
			},
			script: {
				type: "string",
				description:
					"The exact spoken script for the voice message. Keep it concise and natural for speech. Bracketed expression tags (emotional states like [happy], [sad], [tired] or actions like [whispers], [laughs]) can be placed inline to shape the delivery.",
			},
		},
		required: ["title", "script"],
	};

	private resolveThreadId(context: ToolContext): string | undefined {
		return "isThread" in context.channel &&
			typeof context.channel.isThread === "function" &&
			context.channel.isThread()
			? context.channel.id
			: undefined;
	}

	private buildAttachmentName(title: string, extension: string): string {
		const baseName = title
			.trim()
			.replace(/[^A-Za-z0-9_-]+/g, "_")
			.replace(/^_+|_+$/g, "")
			.slice(0, 40);

		const safeBaseName = baseName.length > 0 ? baseName : "voice";
		return `${safeBaseName}.${extension}`;
	}

	/**
	 * Sends a native Discord voice message via raw REST, bypassing discord.js's
	 * MessagePayload serialization which drops unknown attachment fields like
	 * `waveform` and `duration_secs`.
	 *
	 * @returns The sent message ID, or undefined if the request failed
	 */
	private async sendNativeVoiceMessageViaRest(options: {
		webhook: Webhook;
		audioBuffer: Buffer;
		mimeType: string;
		filename: string;
		voiceMeta: VoiceMessageMetadata;
		username?: string;
		avatarUrl?: string | null;
		threadId?: string;
	}): Promise<string | undefined> {
		try {
			const { webhook, audioBuffer, mimeType, filename, voiceMeta, username, avatarUrl, threadId } = options;

			if (!webhook.token) return undefined;

			// Build multipart form — Discord requires payload_json + binary file part
			const form = new FormData();

			const payloadJson: Record<string, unknown> = {
				flags: IS_VOICE_MESSAGE_FLAG,
				attachments: [
					{
						id: 0,
						filename,
						waveform: voiceMeta.waveform,
						duration_secs: voiceMeta.durationSecs,
					},
				],
				allowed_mentions: { parse: [] },
			};

			// Username and avatar override for persona identity
			if (username) payloadJson.username = username;
			// data: URIs cannot be used as avatar_url — only HTTP(S) URLs are accepted
			if (avatarUrl && !avatarUrl.startsWith("data:image/")) {
				payloadJson.avatar_url = avatarUrl;
			}

			form.append("payload_json", JSON.stringify(payloadJson));
			form.append(
				"files[0]",
				new Blob([new Uint8Array(audioBuffer)], { type: mimeType }),
				filename,
			);

			// ?wait=true is required to receive a Message object back (otherwise 204)
			const threadParam = threadId
				? `&thread_id=${encodeURIComponent(threadId)}`
				: "";
			const url = `${DISCORD_API_BASE}/webhooks/${webhook.id}/${webhook.token}?wait=true${threadParam}`;

			const response = await fetch(url, { method: "POST", body: form });

			if (!response.ok) {
				const errorText = await response.text().catch(() => "unknown");
				log.warn(
					`[VoiceWaveform] Discord API rejected native voice message: HTTP ${response.status} — ${errorText}`,
				);
				return undefined;
			}

			const data = (await response.json()) as { id?: string };
			return data.id;
		} catch (error) {
			log.warn("[VoiceWaveform] Exception during native voice message send", error);
			return undefined;
		}
	}

	/**
	 * Sends a native Discord voice message via the bot's REST client, bypassing
	 * webhook delivery. Used when no persona webhook is in scope (e.g. main
	 * persona or non-alter context). Does not support username/avatar overrides.
	 *
	 * @returns The sent message ID, or undefined if the request failed
	 */
	private async sendNativeVoiceMessageViaBotRest(options: {
		channel: ToolContext["channel"];
		audioBuffer: Buffer;
		mimeType: string;
		filename: string;
		voiceMeta: VoiceMessageMetadata;
	}): Promise<string | undefined> {
		try {
			const { channel, audioBuffer, mimeType, filename, voiceMeta } = options;

			// Build multipart form — same payload_json structure as the webhook path
			const form = new FormData();

			const payloadJson: Record<string, unknown> = {
				flags: IS_VOICE_MESSAGE_FLAG,
				attachments: [
					{
						id: 0,
						filename,
						waveform: voiceMeta.waveform,
						duration_secs: voiceMeta.durationSecs,
					},
				],
				allowed_mentions: { parse: [] },
			};

			form.append("payload_json", JSON.stringify(payloadJson));
			form.append(
				"files[0]",
				new Blob([new Uint8Array(audioBuffer)], { type: mimeType }),
				filename,
			);

			// Post directly to the channel via bot identity.
			// passThroughBody: true prevents the REST manager from JSON-serializing
			// the FormData body, which would corrupt the multipart boundary.
			// channel.id is correct for both regular channels and threads.
			const data = (await channel.client.rest.post(
				Routes.channelMessages(channel.id),
				{ body: form, passThroughBody: true },
			)) as { id?: string };

			return data.id;
		} catch (error) {
			log.warn("[VoiceWaveform] Exception during bot REST voice message send", error);
			return undefined;
		}
	}

	async execute(
		args: Record<string, unknown>,
		context: ToolContext,
	): Promise<ToolResult> {
		const validation = this.validateParameters(args);
		if (!validation.isValid) {
			return {
				success: false,
				error: `Invalid parameters: ${validation.errors?.join(", ") || validation.missingParams?.join(", ") || "unknown validation error"}`,
			};
		}

		const title = typeof args.title === "string" ? args.title.trim() : "voice";
		const script = typeof args.script === "string" ? args.script.trim() : "";
		if (!script) {
			return {
				success: false,
				error: "The voice script was empty.",
			};
		}

		const voiceId = context.tomoriState.elevenlabs_voice_id?.trim();
		if (!voiceId) {
			return {
				success: false,
				error:
					"No ElevenLabs voice is configured for the active persona. A server manager can set one with /config voice elevenlabs.",
			};
		}

		const apiKey = await getOptApiKey(
			context.tomoriState.server_id,
			ELEVENLABS_SERVICE_NAME,
		);
		if (!apiKey) {
			return {
				success: false,
				error:
					"No ElevenLabs API key is available for this server. A server manager can set one with /optionalkey elevenlabs set.",
			};
		}

		const synthesisResult = await synthesizeSpeechWithElevenLabs({
			apiKey,
			voiceId,
			script,
		});
		if (!synthesisResult.success || !synthesisResult.audioBuffer) {
			return {
				success: false,
				error:
					synthesisResult.details ||
					"Failed to generate the ElevenLabs voice message.",
			};
		}

		const attachmentName = this.buildAttachmentName(
			title,
			synthesisResult.extension ?? "mp3",
		);
		const threadId = this.resolveThreadId(context);
		const captionText = synthesisResult.cleanedCaptionText ?? "";
		// Strip any MIME parameters (e.g. "audio/mpeg; codecs=mp3" → "audio/mpeg")
		// Discord rejects waveform/duration_secs when the content type isn't a
		// bare audio/* type — it falls back to application/octet-stream otherwise.
		const mimeType = (synthesisResult.contentType ?? "audio/mpeg")
			.split(";")[0]
			.trim();

		// Attempt to generate waveform + duration for Discord's native voice
		// message UI. Falls back gracefully to a plain attachment if it fails.
		const voiceMeta = await generateVoiceMessageMetadata(
			synthesisResult.audioBuffer,
			mimeType,
		);

		let sentMessageId: string | undefined;

		if (!voiceMeta) {
			log.warn("[VoiceWaveform] Waveform generation returned null — falling back to plain attachment");
		}

		// --- Native voice message path ---
		// Bypasses discord.js MessagePayload serialization, which silently drops
		// unknown attachment fields like waveform and duration_secs.
		// Two sub-paths: webhook identity (alter persona) vs. bot identity (main persona).
		if (voiceMeta) {
			if (context.webhook?.token) {
				// 1. Webhook identity path: alter persona with a valid token
				sentMessageId = await this.sendNativeVoiceMessageViaRest({
					webhook: context.webhook,
					audioBuffer: synthesisResult.audioBuffer,
					mimeType,
					filename: attachmentName,
					voiceMeta,
					username: context.personaUsername,
					avatarUrl: context.personaAvatarUrl,
					threadId,
				});
				if (!sentMessageId) {
					log.warn("[VoiceWaveform] Webhook REST send failed — trying bot REST path");
				}
			} else if (context.webhook && !context.webhook.token) {
				// Log when the webhook object exists but Discord nulled out its token
				log.warn(
					`[VoiceWaveform] Webhook token is null (id=${context.webhook.id}) — trying bot REST path`,
				);
			}

			if (!sentMessageId) {
				// 2. Bot identity path: main persona, no webhook, or webhook with no token
				sentMessageId = await this.sendNativeVoiceMessageViaBotRest({
					channel: context.channel,
					audioBuffer: synthesisResult.audioBuffer,
					mimeType,
					filename: attachmentName,
					voiceMeta,
				});
				if (!sentMessageId) {
					log.warn("[VoiceWaveform] Bot REST send failed — falling back to plain attachment");
				}
			}
		}

		// --- Fallback: plain attachment via discord.js ---
		// Used when waveform generation failed or both native REST paths failed.
		if (!sentMessageId) {
			const attachment = new AttachmentBuilder(synthesisResult.audioBuffer, {
				name: attachmentName,
			});

			if (context.webhook && context.personaUsername) {
				const sentMessage = await sendWebhookMessageWithIdentity(
					context.webhook,
					{
						files: [attachment],
						allowedMentions: {
							parse: [],
							repliedUser: false,
						},
						...(threadId ? { threadId } : {}),
					},
					{
						username: context.personaUsername,
						avatarUrl: context.personaAvatarUrl,
						avatarDataUri: context.personaAvatarUrl?.startsWith("data:image/")
							? context.personaAvatarUrl
							: undefined,
					},
				);
				sentMessageId = sentMessage.id;
			} else {
				const sentMessage = await context.channel.send({
					files: [attachment],
				});
				sentMessageId = sentMessage.id;
			}
		}

		// Cache caption text keyed by message ID so the history formatter can
		// inline the clean text in future context passes without re-running STT.
		if (sentMessageId && captionText) {
			setCachedVoiceTranscript(sentMessageId, captionText, "tts");
			log.info(
				`[VoiceCache] SET tts | msg=${sentMessageId} | chars=${captionText.length} | preview="${captionText.slice(0, 60)}${captionText.length > 60 ? "…" : ""}"`,
			);
		}

		// In chat mode, also post the script as a visible blockquote text message
		// so users can read what was said without playing the audio. The LLM will
		// see it naturally from chat history; no extra context injection needed.
		if (sentMessageId && captionText && context.tomoriState.config.voice_transcript_chat_mode) {
			const quotedCaption = `> ${captionText.replace(/\n/g, "\n> ")}`;
			try {
				if (context.webhook && context.personaUsername) {
					await sendWebhookMessageWithIdentity(
						context.webhook,
						{
							content: quotedCaption,
							allowedMentions: { parse: [] },
							...(threadId ? { threadId } : {}),
						},
						{
							username: context.personaUsername,
							avatarUrl: context.personaAvatarUrl,
							avatarDataUri: context.personaAvatarUrl?.startsWith("data:image/")
								? context.personaAvatarUrl
								: undefined,
						},
					);
				} else {
					await context.channel.send({
						content: quotedCaption,
						allowedMentions: { parse: [] },
					});
				}
				log.info(
					`[VoiceChat] Posted TTS transcript | msg=${sentMessageId} | persona="${context.personaUsername ?? "bot"}"`,
				);
			} catch (error) {
				log.warn(
					`[VoiceChat] Failed to post TTS transcript for msg=${sentMessageId}`,
					error,
				);
			}
		}

		return {
			success: true,
			message: "Voice message generated and sent to Discord.",
			endTurn: true,
		};
	}
}
