import {
	MessageFlags,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import { loadSavedProviderConfigs } from "@/utils/db/dbRead";
import { deleteSavedProviderConfig } from "@/utils/db/dbWrite";
import { getCachedTomoriState } from "@/utils/cache/tomoriStateCache";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import {
	replyInfoEmbed,
	promptWithRawModal,
} from "@/utils/discord/interactionHelper";
import type { UserRow, ErrorContext } from "@/types/db/schema";
import type { SelectOption, ModalComponent } from "@/types/discord/modal";
import { getProviderDisplayName } from "@/utils/provider/providerInfoRegistry";
import {
	isCustomProvider,
	deleteCustomLLMEntry,
} from "@/utils/discord/customProviderModal";

// Modal configuration constants
const MODAL_CUSTOM_ID = "config_provider_remove_modal";
const PROVIDER_SELECT_ID = "provider_remove_select";

// Configure the subcommand
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("remove")
		.setDescription(
			localizer("en-US", "commands.config.provider.remove.description"),
		);

/**
 * Removes a saved provider configuration from the database.
 * Only shows providers that have saved configs (excluding the active provider).
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
	// 1. Ensure command is run in a channel context
	if (!interaction.channel) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 2. Load the Tomori state for this server/user
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

	// Track modal submit interaction for error handling in catch block
	let modalSubmitInteraction:
		| import("discord.js").ModalSubmitInteraction
		| undefined;

	try {
		// 3. Load saved provider configs, excluding the currently active provider
		const allSavedConfigs = await loadSavedProviderConfigs(
			tomoriState.server_id,
		);
		const currentProvider = tomoriState.llm.llm_provider.toLowerCase();
		const removableConfigs = allSavedConfigs.filter(
			(c) => c.provider.toLowerCase() !== currentProvider,
		);

		// 4. If no saved configs to remove, show error
		if (removableConfigs.length === 0) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.config.provider.remove.no_saved_title",
				descriptionKey:
					"commands.config.provider.remove.no_saved_description",
				color: ColorCode.WARN,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		// 5. Build select options from removable saved configs
		const selectOptions: SelectOption[] = removableConfigs.map((config) => ({
			label: getProviderDisplayName(config.provider),
			value: config.provider.toLowerCase(),
			description: undefined,
		}));

		// 6. Show modal with provider selection
		const modalComponents: ModalComponent[] = [
			{
				customId: PROVIDER_SELECT_ID,
				labelKey: "commands.config.provider.remove.confirm_title",
				descriptionKey:
					"commands.config.provider.remove.confirm_description",
				placeholder: "commands.config.provider.remove.select_placeholder",
				required: true,
				options: selectOptions,
			},
		];

		const modalResult = await promptWithRawModal(
			interaction,
			locale,
			{
				modalCustomId: MODAL_CUSTOM_ID,
				modalTitleKey: "commands.config.provider.remove.confirm_title",
				components: modalComponents,
			},
			MessageFlags.Ephemeral,
		);

		// 7. Handle modal outcome
		if (modalResult.outcome !== "submit") {
			log.info(
				`Provider remove modal ${modalResult.outcome} for user ${userData.user_id}`,
			);
			return;
		}

		modalSubmitInteraction = modalResult.interaction;
		const selectedProvider = modalResult.values?.[PROVIDER_SELECT_ID];

		if (!modalSubmitInteraction || !selectedProvider) {
			log.error(
				"Provider remove modal result unexpectedly missing interaction or values",
			);
			return;
		}

		// 8. Delete the saved config
		const deleted = await deleteSavedProviderConfig(
			tomoriState.server_id,
			selectedProvider,
		);

		if (!deleted) {
			await replyInfoEmbed(modalSubmitInteraction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 9. Also purge rotation keys for that provider (clean break)
		const { purgeRotationKeysForProvider } = await import(
			"../../../utils/security/keyRotation"
		);
		const purgedCount = await purgeRotationKeysForProvider(
			tomoriState.server_id,
			selectedProvider,
		);
		if (purgedCount > 0) {
			log.info(
				`Purged ${purgedCount} rotation key(s) for removed provider ${selectedProvider}`,
			);
		}

		// 10. If removing custom provider's saved config, clean up the custom LLM entry
		// (only if the custom provider is NOT currently active)
		if (isCustomProvider(selectedProvider)) {
			log.info(
				`Removing saved custom provider config — cleaning up custom LLM entry`,
			);
			await deleteCustomLLMEntry(serverId);
		}

		// 11. Success message
		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "commands.config.provider.remove.success_title",
			descriptionKey:
				"commands.config.provider.remove.success_description",
			descriptionVars: {
				provider: getProviderDisplayName(selectedProvider),
			},
			color: ColorCode.SUCCESS,
		});
	} catch (error) {
		let serverIdForError: number | null = null;
		let tomoriIdForError: number | null = null;
		const errorServerId = interaction.guild?.id ?? interaction.user.id;
		const state = await getCachedTomoriState(errorServerId);
		serverIdForError = state?.server_id ?? null;
		tomoriIdForError = state?.tomori_id ?? null;

		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: serverIdForError,
			tomoriId: tomoriIdForError,
			errorType: "CommandExecutionError",
			metadata: {
				command: "config provider remove",
				guildId: interaction.guild?.id,
				executorDiscordId: interaction.user.id,
			},
		};
		await log.error(
			`Error executing /config provider remove for user ${userData.user_disc_id}`,
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
