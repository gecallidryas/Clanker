import {
	MessageFlags,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "@/utils/cache/tomoriStateCache";
import { replyInfoEmbed } from "@/utils/discord/interactionHelper";
import { ColorCode, log } from "@/utils/misc/logger";
import {
	deleteOptApiKey,
	hasOptApiKey,
} from "@/utils/security/crypto";
import {
	ELEVENLABS_SERVICE_NAME,
} from "@/utils/audio/elevenLabsAccount";
import { localizer } from "@/utils/text/localizer";
import type {
	ErrorContext,
	TomoriState,
	UserRow,
} from "@/types/db/schema";

export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("remove")
		.setDescription(
			localizer("en-US", "commands.optionalkey.elevenlabs.remove.description"),
		);

export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	let tomoriState: TomoriState | null = null;

	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	await interaction.deferReply({ flags: MessageFlags.Ephemeral });

	try {
		tomoriState = await getCachedTomoriState(
			interaction.guild?.id ?? interaction.user.id,
		);
		if (!tomoriState) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.tomori_not_setup_title",
				descriptionKey: "general.errors.tomori_not_setup_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const hasKey = await hasOptApiKey(
			tomoriState.server_id,
			ELEVENLABS_SERVICE_NAME,
		);
		if (!hasKey) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.optionalkey.elevenlabs.remove.no_key_title",
				descriptionKey:
					"commands.optionalkey.elevenlabs.remove.no_key_description",
				color: ColorCode.WARN,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		const isDeleted = await deleteOptApiKey(
			tomoriState.server_id,
			ELEVENLABS_SERVICE_NAME,
		);
		if (!isDeleted) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "optionalkey elevenlabs remove",
					guildId: interaction.guild?.id ?? interaction.user.id,
					serviceName: ELEVENLABS_SERVICE_NAME,
				},
			};
			await log.error(
				"Failed to delete ElevenLabs API key from optional API keys table",
				new Error("deleteOptApiKey returned false"),
				context,
			);

			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		invalidateTomoriStateCache(interaction.guild?.id ?? interaction.user.id);

		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.optionalkey.elevenlabs.remove.success_title",
			descriptionKey:
				"commands.optionalkey.elevenlabs.remove.success_description",
			color: ColorCode.SUCCESS,
			flags: MessageFlags.Ephemeral,
		});
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: tomoriState?.server_id ?? null,
			tomoriId: tomoriState?.tomori_id ?? null,
			errorType: "CommandExecutionError",
			metadata: {
				command: "optionalkey elevenlabs remove",
				guildId: interaction.guild?.id,
				executorDiscordId: interaction.user.id,
				serviceName: ELEVENLABS_SERVICE_NAME,
			},
		};
		await log.error(
			`Error executing /optionalkey elevenlabs remove for user ${userData.user_disc_id}`,
			error as Error,
			context,
		);

		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
	}
}
