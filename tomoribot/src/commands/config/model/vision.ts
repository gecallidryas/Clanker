import type {
	ChatInputCommandInteraction,
	Client,
	SlashCommandSubcommandBuilder,
} from "discord.js";
import { MessageFlags } from "discord.js";
import { sql } from "@/utils/db/client";
import { loadAvailableModelsForProvider } from "../../../utils/db/dbRead";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "../../../utils/cache/tomoriStateCache";
import { localizer } from "../../../utils/text/localizer";
import { log, ColorCode } from "../../../utils/misc/logger";
import {
	replyInfoEmbed,
	promptWithRawModal,
	safeSelectOptionText,
} from "../../../utils/discord/interactionHelper";
import {
	type UserRow,
	type ErrorContext,
	type LlmRow,
	tomoriConfigSchema,
} from "../../../types/db/schema";
import type { SelectOption } from "../../../types/discord/modal";

// Modal configuration constants
const MODAL_CUSTOM_ID = "config_model_vision_modal";
const MODEL_SELECT_ID = "vision_model_select";

/** Special sentinel value representing "clear the vision model" */
const CLEAR_VISION_VALUE = "__clear__";

/**
 * Helper function to get localized LLM description based on user's locale.
 * Only shows vision-relevant capability flags.
 * @param model - LLM model row from database
 * @param locale - User's preferred locale (e.g., "ja", "en-US")
 * @returns Localized description with flags prepended
 */
function getLocalizedDescription(model: LlmRow, locale: string): string {
	// Normalize locale to handle variations (e.g., "ja-JP" -> "ja")
	const normalizedLocale = locale.toLowerCase().split("-")[0];

	const description =
		normalizedLocale === "ja"
			? model.ja_description
			: model.llm_description;

	const baseDescription =
		description || model.llm_description || `${model.llm_provider} model`;

	// Build flags array based on model capabilities
	const flags: string[] = [];
	if (model.is_free) flags.push("FREE");
	if (model.has_tools) flags.push("TOOLS");
	if (model.sees_images) flags.push("IMG");
	if (model.sees_videos) flags.push("VID");
	if (model.supports_structoutput) flags.push("STRUCT");

	const flagPrefix = flags.length > 0 ? `(${flags.join("+")}) ` : "";
	return `${flagPrefix}${baseDescription}`;
}

// Configure the subcommand
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("vision")
		.setDescription(
			localizer("en-US", "commands.config.model.vision.description"),
		);

/**
 * Sets a dedicated vision model for image analysis.
 * When set, non-vision chat models gain the `analyze_image` tool to delegate
 * image analysis to this vision model.
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
	// 1. Ensure command is run in a channel
	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	// 2. Load the Tomori state for this server
	const serverId = interaction.guild?.id ?? interaction.user.id;
	const tomoriState = await getCachedTomoriState(serverId);
	if (!tomoriState) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.tomori_not_setup_title",
			descriptionKey: "general.errors.tomori_not_setup_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 3. Check if an API key is configured
	if (!tomoriState.config.api_key) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.config.model.vision.no_api_key_title",
			descriptionKey: "commands.config.model.vision.no_api_key_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 4. Load vision-capable models for the current provider (sees_images = true)
	const currentProvider = tomoriState.llm.llm_provider.toLowerCase();
	const allModels = await loadAvailableModelsForProvider(currentProvider);
	const visionModels = allModels?.filter((m) => m.sees_images) ?? [];

	if (visionModels.length === 0) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.config.model.vision.no_models_title",
			descriptionKey: "commands.config.model.vision.no_models_description",
			descriptionVars: { provider: currentProvider },
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// Track modal state for error handling
	let modalSubmitInteraction:
		| import("discord.js").ModalSubmitInteraction
		| undefined;
	let selectedModel: LlmRow | null = null;

	try {
		// 5. Build select options: vision models + "clear" option
		const modelSelectOptions: SelectOption[] = [
			// "None" option to clear the vision model
			{
				label: safeSelectOptionText(
					localizer(locale, "commands.config.model.vision.clear_option"),
				),
				value: CLEAR_VISION_VALUE,
				description: "",
			},
			// Vision-capable models
			...visionModels.map((model) => ({
				label: safeSelectOptionText(model.llm_codename),
				value: safeSelectOptionText(model.llm_codename),
				description: safeSelectOptionText(
					getLocalizedDescription(model, userData.language_pref),
				),
			})),
		];

		// 6. Show the modal with vision model selection
		const modalResult = await promptWithRawModal(
			interaction,
			locale,
			{
				modalCustomId: MODAL_CUSTOM_ID,
				modalTitleKey: "commands.config.model.vision.modal_title",
				components: [
					{
						customId: MODEL_SELECT_ID,
						labelKey: "commands.config.model.vision.select_label",
						descriptionKey: "commands.config.model.vision.select_description",
						placeholder: "commands.config.model.vision.select_placeholder",
						required: true,
						options: modelSelectOptions,
					},
				],
			},
			MessageFlags.Ephemeral,
		);

		// 7. Handle modal outcome
		if (modalResult.outcome !== "submit") {
			log.info(
				`Vision model selection modal ${modalResult.outcome} for user ${userData.user_id}`,
			);
			return;
		}

		// biome-ignore lint/style/noNonNullAssertion: Modal submission outcome "submit" guarantees these values exist
		modalSubmitInteraction = modalResult.interaction!;
		// biome-ignore lint/style/noNonNullAssertion: Modal submission outcome "submit" guarantees these values exist
		const selectedValue = modalResult.values![MODEL_SELECT_ID];

		// 8. Handle "clear" selection — remove vision model
		if (selectedValue === CLEAR_VISION_VALUE) {
			// Check if already cleared
			if (!tomoriState.config.vision_llm_id) {
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey: "commands.config.model.vision.cleared_title",
					descriptionKey: "commands.config.model.vision.cleared_description",
					color: ColorCode.WARN,
				});
				return;
			}

			const [updatedRow] = await sql`
				UPDATE tomori_configs
				SET vision_llm_id = NULL
				WHERE server_id = ${tomoriState.server_id}
				RETURNING *
			`;

			const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);
			if (!validatedConfig.success || !updatedRow) {
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey: "general.errors.update_failed_title",
					descriptionKey: "general.errors.update_failed_description",
					color: ColorCode.ERROR,
				});
				return;
			}

			invalidateTomoriStateCache(serverId);

			await replyInfoEmbed(modalSubmitInteraction, locale, {
				titleKey: "commands.config.model.vision.cleared_title",
				descriptionKey: "commands.config.model.vision.cleared_description",
				color: ColorCode.SUCCESS,
			});
			return;
		}

		// 9. Find the selected vision model by codename
		selectedModel =
			visionModels.find((model) => model.llm_codename === selectedValue) ?? null;

		if (!selectedModel) {
			await replyInfoEmbed(modalSubmitInteraction, locale, {
				titleKey: "commands.config.model.vision.invalid_model_title",
				descriptionKey: "commands.config.model.vision.invalid_model_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 10. Check if already selected
		if (selectedModel.llm_id === tomoriState.config.vision_llm_id) {
			await replyInfoEmbed(modalSubmitInteraction, locale, {
				titleKey: "commands.config.model.vision.already_selected_title",
				descriptionKey: "commands.config.model.vision.already_selected_description",
				descriptionVars: { model_name: selectedModel.llm_codename },
				color: ColorCode.WARN,
			});
			return;
		}

		// 11. Update vision_llm_id in the database
		const [updatedRow] = await sql`
			UPDATE tomori_configs
			SET vision_llm_id = ${selectedModel.llm_id}
			WHERE server_id = ${tomoriState.server_id}
			RETURNING *
		`;

		// 12. Validate the returned data
		const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);
		if (!validatedConfig.success || !updatedRow) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "config model vision",
					guildId: serverId,
					selectedModelCodename: selectedModel.llm_codename,
					targetVisionLlmId: selectedModel.llm_id,
					validationErrors: validatedConfig.success
						? null
						: validatedConfig.error.flatten(),
				},
			};
			await log.error(
				"Failed to update or validate vision model config after DB update",
				validatedConfig.success
					? new Error("Database update returned no rows or unexpected data")
					: new Error("Updated config data failed validation"),
				context,
			);

			await replyInfoEmbed(modalSubmitInteraction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 13. Invalidate cache so next message gets fresh config
		invalidateTomoriStateCache(serverId);

		// 14. Success message (with tool warning if chat model lacks tool support)
		const descriptionKey = tomoriState.llm.has_tools
			? "commands.config.model.vision.success_description"
			: "commands.config.model.vision.success_no_tools_description";

		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "commands.config.model.vision.success_title",
			descriptionKey,
			descriptionVars: {
				model_name: selectedModel.llm_codename,
				chat_model: tomoriState.llm.llm_codename,
			},
			color: ColorCode.SUCCESS,
		});
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: tomoriState?.server_id ?? null,
			tomoriId: tomoriState?.tomori_id ?? null,
			errorType: "CommandExecutionError",
			metadata: {
				command: "config model vision",
				guildId: serverId,
				executorDiscordId: interaction.user.id,
				targetVisionLlmIdAttempted: selectedModel?.llm_id,
			},
		};
		await log.error(
			`Error executing /config model vision for user ${userData.user_disc_id}`,
			error as Error,
			context,
		);

		const replyTarget = modalSubmitInteraction ?? interaction;
		await replyInfoEmbed(replyTarget, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
	}
}
