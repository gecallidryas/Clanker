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
import {
	replyInfoEmbed,
	replySummaryEmbed,
} from "@/utils/discord/interactionHelper";
import { commandRegistry } from "@/utils/discord/commandRegistry";
import { ColorCode, log } from "@/utils/misc/logger";
import { storeOptApiKey } from "@/utils/security/crypto";
import {
	ELEVENLABS_SERVICE_NAME,
	validateElevenLabsApiKey,
} from "@/utils/audio/elevenLabsAccount";
import { localizer } from "@/utils/text/localizer";
import type {
	ErrorContext,
	TomoriState,
	UserRow,
} from "@/types/db/schema";

const MIN_KEY_LENGTH = 10;

export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("set")
		.setDescription(
			localizer("en-US", "commands.optionalkey.elevenlabs.set.description"),
		)
		.addStringOption((option) =>
			option
				.setName("key")
				.setDescription(
					localizer(
						"en-US",
						"commands.optionalkey.elevenlabs.set.key_description",
					),
				)
				.setRequired(true),
		);

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
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	await interaction.deferReply({ flags: MessageFlags.Ephemeral });

	let apiKey: string | null = null;
	let tomoriState: TomoriState | null = null;

	try {
		apiKey = interaction.options.getString("key", true).trim();
		if (apiKey.length < MIN_KEY_LENGTH) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.optionalkey.elevenlabs.set.invalid_key_title",
				descriptionKey:
					"commands.optionalkey.elevenlabs.set.invalid_key_description",
				color: ColorCode.ERROR,
			});
			return;
		}

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

		const validationResult = await validateElevenLabsApiKey(apiKey);
		if (!validationResult.success) {
			log.info(
				`ElevenLabs API key validation failed for server ${tomoriState.server_id}: HTTP ${validationResult.statusCode ?? "?"} — ${validationResult.details ?? validationResult.errorKind ?? "unknown"}`,
			);
			await replyInfoEmbed(interaction, locale, {
				titleKey:
					"commands.optionalkey.elevenlabs.set.key_validation_failed_title",
				descriptionKey:
					"commands.optionalkey.elevenlabs.set.key_validation_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const isStored = await storeOptApiKey(
			tomoriState.server_id,
			ELEVENLABS_SERVICE_NAME,
			apiKey,
		);
		if (!isStored) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "optionalkey elevenlabs set",
					guildId: interaction.guild?.id ?? interaction.user.id,
					serviceName: ELEVENLABS_SERVICE_NAME,
				},
			};
			await log.error(
				"Failed to store ElevenLabs API key in optional API keys table",
				new Error("storeOptApiKey returned false"),
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

		// Resolve command mentions for the next-steps fields
		const configVoiceElevenlabsMention = commandRegistry.getCommandMention(
			"config",
			"voice",
			"elevenlabs",
		);
		const configVoiceTranscriptsMention = commandRegistry.getCommandMention(
			"config",
			"voice",
			"transcripts",
		);

		await replySummaryEmbed(
			interaction,
			locale,
			{
				titleKey: "commands.optionalkey.elevenlabs.set.success_title",
				descriptionKey:
					"commands.optionalkey.elevenlabs.set.success_description",
				color: ColorCode.SUCCESS,
				fields: [
					{
						nameKey:
							"commands.optionalkey.elevenlabs.set.success_voices_title",
						value: localizer(
							locale,
							"commands.optionalkey.elevenlabs.set.success_voices_description",
							{ configVoiceElevenlabs: configVoiceElevenlabsMention },
						),
						inline: false,
					},
					{
						nameKey:
							"commands.optionalkey.elevenlabs.set.success_custom_voices_title",
						value: localizer(
							locale,
							"commands.optionalkey.elevenlabs.set.success_custom_voices_description",
							{ configVoiceElevenlabs: configVoiceElevenlabsMention },
						),
						inline: false,
					},
					{
						nameKey:
							"commands.optionalkey.elevenlabs.set.success_transcript_mode_title",
						value: localizer(
							locale,
							"commands.optionalkey.elevenlabs.set.success_transcript_mode_description",
							{ configVoiceTranscripts: configVoiceTranscriptsMention },
						),
						inline: false,
					},
				],
			},
			MessageFlags.Ephemeral,
		);
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: tomoriState?.server_id ?? null,
			tomoriId: tomoriState?.tomori_id ?? null,
			errorType: "CommandExecutionError",
			metadata: {
				command: "optionalkey elevenlabs set",
				guildId: interaction.guild?.id,
				executorDiscordId: interaction.user.id,
				serviceName: ELEVENLABS_SERVICE_NAME,
			},
		};
		await log.error(
			`Error executing /optionalkey elevenlabs set for user ${userData.user_disc_id}`,
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
