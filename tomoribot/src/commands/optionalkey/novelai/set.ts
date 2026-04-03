/**
 * /optionalkey novelai set
 * Validates and stores a NovelAI API key for the server.
 * When set, the generate_image_nai tool becomes available regardless of the active LLM provider.
 * Optional: disable_other_imggen flag hides the standard generate_image tool when this key is present.
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
import { updateTomoriConfig } from "../../../utils/db/dbWrite";

/** Minimum length for a valid NovelAI API key */
const MIN_KEY_LENGTH = 10;

/** NovelAI account API base URL for key validation */
const NOVELAI_ACCOUNT_API_URL = "https://api.novelai.net";

/** Timeout for validation request in milliseconds */
const VALIDATION_TIMEOUT_MS = 10_000;

/**
 * Configure the subcommand for setting NovelAI API key
 * @param subcommand - Discord slash command subcommand builder
 * @returns Configured subcommand builder
 */
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("set")
		.setDescription(
			localizer("en-US", "commands.optionalkey.novelai.set.description"),
		)
		.addStringOption((option) =>
			option
				.setName("key")
				.setDescription(
					localizer(
						"en-US",
						"commands.optionalkey.novelai.set.key_description",
					),
				)
				.setRequired(true),
		)
		.addStringOption((option) =>
			option
				.setName("disable_other_imggen")
				.setDescription(
					localizer(
						"en-US",
						"commands.optionalkey.novelai.set.disable_other_imggen_description",
					),
				)
				.addChoices(
					{ name: localizer("en-US", "commands.choices.enable"), value: "enable" },
					{ name: localizer("en-US", "commands.choices.disable"), value: "disable" },
				)
				.setRequired(false),
		);

/**
 * Validates a NovelAI API key by calling the subscription endpoint.
 * A valid key returns 200 with subscription data; invalid keys return 401.
 * @param apiKey - The API key to validate
 * @returns True if the key is valid and the account is active
 */
async function validateNovelAiApiKey(apiKey: string): Promise<boolean> {
	try {
		const controller = new AbortController();
		const timeoutId = setTimeout(
			() => controller.abort(),
			VALIDATION_TIMEOUT_MS,
		);

		const response = await fetch(
			`${NOVELAI_ACCOUNT_API_URL}/user/subscription`,
			{
				method: "GET",
				headers: {
					Accept: "application/json",
					Authorization: `Bearer ${apiKey}`,
				},
				signal: controller.signal,
			},
		);

		clearTimeout(timeoutId);
		return response.ok;
	} catch {
		return false;
	}
}

/**
 * Sets the NovelAI API key for the server's optional API keys
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
		// 3. Get the API key and optional flag from options
		apiKey = interaction.options.getString("key", true);
		const disableOtherImggen =
			interaction.options.getString("disable_other_imggen") === "enable";

		// 4. Basic format validation
		if (!apiKey || apiKey.length < MIN_KEY_LENGTH) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.optionalkey.novelai.set.invalid_key_title",
				descriptionKey:
					"commands.optionalkey.novelai.set.invalid_key_description",
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

		// 6. Validate the API key by calling NovelAI subscription endpoint
		const isValid = await validateNovelAiApiKey(apiKey);
		if (!isValid) {
			log.info(
				`NovelAI API key validation failed for server ${tomoriState.server_id}`,
			);
			await replyInfoEmbed(interaction, locale, {
				titleKey:
					"commands.optionalkey.novelai.set.key_validation_failed_title",
				descriptionKey:
					"commands.optionalkey.novelai.set.key_validation_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 7. Store the validated API key
		const isStored = await storeOptApiKey(
			tomoriState.server_id,
			"novelai",
			apiKey,
		);

		if (!isStored) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "optionalkey novelai set",
					guildId: interaction.guild?.id ?? interaction.user.id,
					serviceName: "novelai",
				},
			};
			await log.error(
				"Failed to store NovelAI API key in optional API keys table",
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

		// 8. Update the nai_exclusive_imggen flag in tomori_configs
		await updateTomoriConfig(tomoriState.server_id, {
			nai_exclusive_imggen: disableOtherImggen,
		});

		// 9. Invalidate cache so next message gets fresh config
		invalidateTomoriStateCache(interaction.guild?.id ?? interaction.user.id);

		// 10. Success message — include note about exclusive mode if enabled
		const successDescriptionKey = disableOtherImggen
			? "commands.optionalkey.novelai.set.success_exclusive_description"
			: "commands.optionalkey.novelai.set.success_description";

		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.optionalkey.novelai.set.success_title",
			descriptionKey: successDescriptionKey,
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
				command: "optionalkey novelai set",
				guildId: interaction.guild?.id,
				executorDiscordId: interaction.user.id,
				serviceName: "novelai",
			},
		};
		await log.error(
			`Error executing /optionalkey novelai set for user ${userData.user_disc_id}`,
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
