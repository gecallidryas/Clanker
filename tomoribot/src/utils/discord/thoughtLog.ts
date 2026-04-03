import {
	EmbedBuilder,
	type BaseGuildTextChannel,
	type Client,
} from "discord.js";
import type { ThoughtLogPayload } from "@/types/provider/interfaces";
import { getLlmDisplayName } from "@/utils/provider/modelDisplay";
import { ColorCode, log } from "@/utils/misc/logger";
import { localizer } from "@/utils/text/localizer";
import type { StreamContext } from "@/types/stream/interfaces";
import type { TomoriState } from "@/types/db/schema";
import {
	getOrCreateWebhook,
	resolvePersonaWebhookIdentity,
	sendWebhookMessagesWithIdentity,
	type ResolvedWebhookIdentity,
} from "@/utils/discord/webhookManager";

const EMBED_DESCRIPTION_LIMIT = 4096;

function normalizeThoughtLogText(value?: string): string | undefined {
	const trimmed = value?.trim();
	return trimmed ? trimmed : undefined;
}

function takeEmbedChunk(
	value: string,
	maxLength: number,
): {
	chunk: string;
	remaining: string;
} {
	if (value.length <= maxLength) {
		return {
			chunk: value.trim(),
			remaining: "",
		};
	}

	let splitIndex = Math.max(
		value.lastIndexOf("\n", maxLength),
		value.lastIndexOf(" ", maxLength),
	);
	if (splitIndex <= 0) {
		splitIndex = maxLength;
	} else {
		splitIndex += 1;
	}

	return {
		chunk: value.slice(0, splitIndex).trim(),
		remaining: value.slice(splitIndex).trim(),
	};
}

function buildThoughtLogEmbeds(args: {
	locale: string;
	tomoriState: TomoriState;
	sourceChannel: StreamContext["channel"];
	thoughtLog: ThoughtLogPayload;
}): EmbedBuilder[] {
	const { locale, tomoriState, sourceChannel, thoughtLog } = args;
	const embeds: EmbedBuilder[] = [];
	// Raw jump URL auto-links in Discord embeds; masked links with channel mentions don't render cleanly.
	const sourceLine = thoughtLog.firstReplyUrl ?? sourceChannel.toString();
	const description = localizer(locale, "genai.thought_log.description", {
		source_line: sourceLine,
	}).slice(0, EMBED_DESCRIPTION_LIMIT);
	const footerText = localizer(locale, "genai.thought_log.footer", {
		provider: tomoriState.llm.llm_provider,
		model: getLlmDisplayName(
			tomoriState.llm,
			tomoriState.config.custom_model_name,
		),
	});

	const sections = [
		{
			label: localizer(locale, "genai.thought_log.summary_field"),
			content: normalizeThoughtLogText(thoughtLog.summary),
		},
		{
			label: localizer(locale, "genai.thought_log.raw_field"),
			content: normalizeThoughtLogText(thoughtLog.raw),
		},
	].filter(
		(section): section is { label: string; content: string } =>
			typeof section.content === "string" && section.content.length > 0,
	);

	if (sections.length === 0) {
		embeds.push(
			new EmbedBuilder()
				.setColor(ColorCode.INFO)
				.setTitle(localizer(locale, "genai.thought_log.title"))
				.setDescription(description)
				.setTimestamp()
				.setFooter({ text: footerText }),
		);
		return embeds;
	}

	let metadataAttached = false;
	for (const section of sections) {
		let remaining = section.content;

		while (remaining.length > 0) {
			const sectionHeader = `**${section.label}**\n`;
			const prefix =
				!metadataAttached && embeds.length === 0
					? `${description}\n\n${sectionHeader}`
					: sectionHeader;
			const availableLength = Math.max(
				1,
				EMBED_DESCRIPTION_LIMIT - prefix.length,
			);
			const { chunk, remaining: nextRemaining } = takeEmbedChunk(
				remaining,
				availableLength,
			);

			embeds.push(
				new EmbedBuilder()
					.setColor(ColorCode.INFO)
					.setTitle(localizer(locale, "genai.thought_log.title"))
					.setDescription(`${prefix}${chunk}`)
					.setTimestamp()
					.setFooter({ text: footerText }),
			);

			remaining = nextRemaining;
			metadataAttached = true;
		}
	}

	return embeds;
}

function appendThoughtSection(
	existing?: string,
	incoming?: string,
): string | undefined {
	const normalizedExisting = normalizeThoughtLogText(existing);
	const normalizedIncoming = normalizeThoughtLogText(incoming);
	if (!normalizedIncoming) {
		return normalizedExisting;
	}
	if (!normalizedExisting || normalizedExisting === normalizedIncoming) {
		return normalizedIncoming;
	}
	if (normalizedExisting.includes(normalizedIncoming)) {
		return normalizedExisting;
	}
	if (normalizedIncoming.includes(normalizedExisting)) {
		return normalizedIncoming;
	}

	return `${normalizedExisting}\n\n${normalizedIncoming}`;
}

export function mergeThoughtLogPayload(
	base?: ThoughtLogPayload | null,
	next?: ThoughtLogPayload | null,
): ThoughtLogPayload | undefined {
	const summary = appendThoughtSection(base?.summary, next?.summary);
	const raw = appendThoughtSection(base?.raw, next?.raw);
	const firstReplyUrl = base?.firstReplyUrl || next?.firstReplyUrl;

	if (!summary && !raw && !firstReplyUrl) {
		return undefined;
	}

	return {
		summary,
		raw,
		firstReplyUrl,
	};
}

export function hasThoughtLogContent(payload?: ThoughtLogPayload | null): boolean {
	return Boolean(
		normalizeThoughtLogText(payload?.summary) ||
			normalizeThoughtLogText(payload?.raw),
	);
}

interface SendThoughtLogEmbedArgs {
	client: Client;
	locale: string;
	tomoriState: TomoriState;
	sourceChannel: StreamContext["channel"];
	thoughtLogChannelId: string;
	thoughtLog: ThoughtLogPayload;
	owner?: ThoughtLogOwner;
}

export type ThoughtLogOwner =
	| { type: "default" }
	| { type: "persona"; persona: TomoriState }
	| {
			type: "user_impersonation";
			username: string;
			avatarUrl?: string | null;
	  };

async function resolveThoughtLogOwnerIdentity(
	owner: ThoughtLogOwner | undefined,
	thoughtLogChannel: BaseGuildTextChannel,
): Promise<ResolvedWebhookIdentity | null> {
	if (!owner || owner.type === "default") {
		return null;
	}

	if (owner.type === "user_impersonation") {
		return {
			username: owner.username,
			avatarUrl: owner.avatarUrl ?? undefined,
		};
	}

	if (!owner.persona.is_alter) {
		return null;
	}

	return await resolvePersonaWebhookIdentity(
		owner.persona,
		thoughtLogChannel.guild,
	);
}

export async function sendThoughtLogEmbed({
	client,
	locale,
	tomoriState,
	sourceChannel,
	thoughtLogChannelId,
	thoughtLog,
	owner,
}: SendThoughtLogEmbedArgs): Promise<void> {
	if (!hasThoughtLogContent(thoughtLog)) {
		return;
	}

	const thoughtLogChannel = await client.channels
		.fetch(thoughtLogChannelId)
		.catch(() => null);

	if (
		!thoughtLogChannel ||
		!("send" in thoughtLogChannel) ||
		typeof thoughtLogChannel.send !== "function" ||
		("isDMBased" in thoughtLogChannel &&
			typeof thoughtLogChannel.isDMBased === "function" &&
			thoughtLogChannel.isDMBased())
	) {
		log.warn(
			`Thought log channel ${thoughtLogChannelId} is missing or unavailable. Skipping thought log post.`,
		);
		return;
	}

	const embeds = buildThoughtLogEmbeds({
		locale,
		tomoriState,
		sourceChannel,
		thoughtLog,
	});

	try {
		const payloads = embeds.map((embed) => ({
			embeds: [embed],
			allowedMentions: { parse: [] as [] },
		}));
		const shouldUseWebhook =
			owner &&
			owner.type !== "default" &&
			"fetchWebhooks" in thoughtLogChannel &&
			"createWebhook" in thoughtLogChannel;

		if (shouldUseWebhook) {
			const webhookResult = await getOrCreateWebhook(
				thoughtLogChannel as BaseGuildTextChannel,
			);
			const identity = await resolveThoughtLogOwnerIdentity(
				owner,
				thoughtLogChannel as BaseGuildTextChannel,
			);

			if (webhookResult.webhook && identity?.username) {
				await sendWebhookMessagesWithIdentity(
					webhookResult.webhook,
					payloads,
					identity,
					thoughtLogChannel.id,
				);
			} else {
				for (const payload of payloads) {
					await thoughtLogChannel.send(payload);
				}
			}
		} else {
			for (const payload of payloads) {
				await thoughtLogChannel.send(payload);
			}
		}
		log.info(
			`Posted ${embeds.length} thought log embed(s) to channel ${thoughtLogChannelId}`,
		);
	} catch (error) {
		log.warn(
			`Failed to send thought log embed to channel ${thoughtLogChannelId}`,
			error instanceof Error ? error : new Error(String(error)),
		);
	}
}
