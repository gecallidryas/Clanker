import { log } from "@/utils/misc/logger";
import {
	sendStandardEmbed,
	type WebhookEmbedContext,
} from "@/utils/discord/embedHelper";
import type { StandardEmbedOptions } from "@/types/discord/embed";

type ToolProgressChannel = Parameters<typeof sendStandardEmbed>[0];

export async function sendToolProgressNotice(
	channel: ToolProgressChannel,
	locale: string,
	options: StandardEmbedOptions,
	webhookContext: WebhookEmbedContext | undefined,
	logLabel: string,
): Promise<void> {
	try {
		await sendStandardEmbed(channel, locale, options, webhookContext);
	} catch (error) {
		log.warn(
			`${logLabel}: Failed to send progress notification embed`,
			error as Error,
		);
	}
}
