/**
 * /optionalkey google set
 * Validates and stores a Google API key for the server.
 * Used primarily for Gemini image segmentation (inpainting masks).
 */

import {
	MessageFlags,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "../../../utils/cache/tomoriStateCache";
import { localizer } from "../../../utils/text/localizer";
import { log, ColorCode } from "../../../utils/misc/logger";
import { replyInfoEmbed } from "../../../utils/discord/interactionHelper";
import type {
	UserRow,
	ErrorContext,
	TomoriState,
} from "../../../types/db/schema";
import { storeOptApiKey } from "../../../utils/security/crypto";

/** Minimum length for a valid Google API key */
const MIN_KEY_LENGTH = 10;

/** Timeout for validation request in milliseconds */
const VALIDATION_TIMEOUT_MS = 5000;

/**
 * Configure the subcommand for setting Google API key
 * @param subcommand - Discord slash command subcommand builder
 * @returns Configured subcommand builder
 */
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("set")
		.setDescription(
			localizer("en-US", "commands.optionalkey.google.set.description"),
		)
		.addStringOption((option) =>
			option
				.setName("key")
				.setDescription(
					localizer("en-US", "commands.optionalkey.google.set.key_description"),
				)
				.setRequired(true),
		);

/**
 * Validates a Google API key by calling the Gemini list-models endpoint.
 * @param apiKey - The API key to validate
 * @returns True if the key is valid
 */
async function validateGoogleApiKey(apiKey: string): Promise<boolean> {
	try {
		const response = await Promise.race([
			fetch(
				`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`,
				{ method: "GET" },
			),
			new Promise<Response>((_resolve, reject) =>
				setTimeout(() => reject(new Error("Timeout")), VALIDATION_TIMEOUT_MS),
			),
		]);

		return response.ok;
	} catch {
		return false;
	}
}

/**
 * Sets the Google API key for the server's optional API keys
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
	// 1. Ensure command is run in a guild
	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 2. Defer the interaction before async work to prevent timeout
	await interaction.deferReply({ flags: MessageFlags.Ephemeral });

	let apiKey: string | null = null;
	let tomoriState: TomoriState | null = null;

	try {
		// 3. Get the API key from options
		apiKey = interaction.options.getString("key", true);

		// 4. Basic format validation
		if (!apiKey || apiKey.length < MIN_KEY_LENGTH) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.optionalkey.google.set.invalid_key_title",
				descriptionKey:
					"commands.optionalkey.google.set.invalid_key_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 5. Load the Tomori state for this server
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

		// 6. Validate the API key by calling Gemini list-models endpoint
		const isValid = await validateGoogleApiKey(apiKey);
		if (!isValid) {
			log.info(
				`Google API key validation failed for server ${tomoriState.server_id}`,
			);
			await replyInfoEmbed(interaction, locale, {
				titleKey:
					"commands.optionalkey.google.set.key_validation_failed_title",
				descriptionKey:
					"commands.optionalkey.google.set.key_validation_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 7. Store the validated API key
		const isStored = await storeOptApiKey(
			tomoriState.server_id,
			"google",
			apiKey,
		);

		if (!isStored) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "optionalkey google set",
					guildId: interaction.guild?.id ?? interaction.user.id,
					serviceName: "google",
				},
			};
			await log.error(
				"Failed to store Google API key in optional API keys table",
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

		// 8. Invalidate cache so next message gets fresh config
		invalidateTomoriStateCache(interaction.guild?.id ?? interaction.user.id);

		// 9. Success message
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.optionalkey.google.set.success_title",
			descriptionKey: "commands.optionalkey.google.set.success_description",
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
				command: "optionalkey google set",
				guildId: interaction.guild?.id,
				executorDiscordId: interaction.user.id,
				serviceName: "google",
			},
		};
		await log.error(
			`Error executing /optionalkey google set for user ${userData.user_disc_id}`,
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
