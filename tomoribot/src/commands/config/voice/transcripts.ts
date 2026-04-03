import type {
	ChatInputCommandInteraction,
	Client,
	SlashCommandSubcommandBuilder,
} from "discord.js";
import { MessageFlags } from "discord.js";
import { sql } from "@/utils/db/client";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "@/utils/cache/tomoriStateCache";
import {
	type ErrorContext,
	type UserRow,
	tomoriConfigSchema,
} from "@/types/db/schema";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import { replyInfoEmbed } from "@/utils/discord/interactionHelper";

// Configure the subcommand
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("transcripts")
		.setDescription(
			localizer("en-US", "commands.config.voice.transcripts.description"),
		)
		.addStringOption((option) =>
			option
				.setName("set")
				.setDescription(
					localizer(
						"en-US",
						"commands.config.voice.transcripts.set_description",
					),
				)
				.setRequired(true)
				.addChoices(
					{
						name: localizer("en-US", "commands.config.options.enable"),
						value: "enable",
					},
					{
						name: localizer("en-US", "commands.config.options.disable"),
						value: "disable",
					},
				),
		);

/**
 * Toggles voice transcript chat mode for this server.
 *
 * When enabled, voice messages are transcribed and posted as visible blockquote
 * chat messages impersonating the original sender via webhook. The internal
 * transcript cache is bypassed and audio is never sent to the AI model directly.
 *
 * @param _client - Discord client instance
 * @param interaction - Command interaction
 * @param userData - User data from database
 * @param locale - Locale of the interaction
 */
export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	const serverDiscId = interaction.guild?.id ?? interaction.user.id;
	await interaction.deferReply({ flags: MessageFlags.Ephemeral });

	try {
		const setAction = interaction.options.getString("set", true);
		const isEnabled = setAction === "enable";

		const tomoriState = await getCachedTomoriState(serverDiscId);
		if (!tomoriState) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.tomori_not_setup_title",
				descriptionKey: "general.errors.tomori_not_setup_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// Guard against no-op updates
		const currentSetting =
			tomoriState.config.voice_transcript_chat_mode ?? false;
		if (currentSetting === isEnabled) {
			await replyInfoEmbed(interaction, locale, {
				titleKey:
					"commands.config.voice.transcripts.already_set_title",
				descriptionKey: isEnabled
					? "commands.config.voice.transcripts.already_enabled_description"
					: "commands.config.voice.transcripts.already_disabled_description",
				color: ColorCode.WARN,
			});
			return;
		}

		// 1. Write to DB
		const [updatedRow] = await sql`
			UPDATE tomori_configs
			SET voice_transcript_chat_mode = ${isEnabled}
			WHERE server_id = ${tomoriState.server_id}
			RETURNING *
		`;

		if (!updatedRow) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "config voice transcripts",
					voiceTranscriptChatMode: isEnabled,
					targetTable: "tomori_configs",
				},
			};
			await log.error(
				"Failed to update voice_transcript_chat_mode config",
				new Error("Database update returned no rows"),
				context,
			);
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);
		if (!validatedConfig.success) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				errorType: "SchemaValidationError",
				metadata: {
					command: "config voice transcripts",
					validationErrors: validatedConfig.error.flatten(),
				},
			};
			await log.error(
				"Failed to validate updated config",
				validatedConfig.error,
				context,
			);
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 2. Invalidate cache only after a successful write
		invalidateTomoriStateCache(serverDiscId);

		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.config.voice.transcripts.success_title",
			descriptionKey: isEnabled
				? "commands.config.voice.transcripts.enabled_success"
				: "commands.config.voice.transcripts.disabled_success",
			color: isEnabled ? ColorCode.SUCCESS : ColorCode.WARN,
		});
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: (await getCachedTomoriState(serverDiscId))?.server_id,
			errorType: "CommandExecutionError",
			metadata: {
				command: "config voice transcripts",
				options: interaction.options?.data,
			},
		};
		await log.error(
			"Error in /config voice transcripts command",
			error as Error,
			context,
		);

		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
		});
	}
}
