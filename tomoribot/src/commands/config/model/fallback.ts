import type {
	ChatInputCommandInteraction,
	ButtonInteraction,
	Client,
	SlashCommandSubcommandBuilder,
} from "discord.js";
import {
	MessageFlags,
	ButtonBuilder,
	ButtonStyle,
	ActionRowBuilder,
} from "discord.js";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "../../../utils/cache/tomoriStateCache";
import { loadAvailableModelsForProvider } from "../../../utils/db/dbRead";
import { setFallbackLlms } from "../../../utils/db/dbWrite";
import { localizer } from "../../../utils/text/localizer";
import { log, ColorCode } from "../../../utils/misc/logger";
import {
	replyInfoEmbed,
	promptWithRawModal,
	safeSelectOptionText,
} from "../../../utils/discord/interactionHelper";
import { createStandardEmbed } from "../../../utils/discord/embedHelper";
import type { LlmRow, UserRow } from "../../../types/db/schema";
import type { SelectOption } from "../../../types/discord/modal";

// Modal field identifiers
// Note: MODAL_CUSTOM_ID is generated per-invocation (see execute()) to prevent stale
// awaitModalSubmit listeners from a previous run resolving on the same submission.
const SLOT_IDS = [
	"fallback_slot_1",
	"fallback_slot_2",
	"fallback_slot_3",
	"fallback_slot_4",
	"fallback_slot_5",
] as const;

const SLOT_LABEL_KEYS = [
	"commands.config.model.fallback.slot_1_label",
	"commands.config.model.fallback.slot_2_label",
	"commands.config.model.fallback.slot_3_label",
	"commands.config.model.fallback.slot_4_label",
	"commands.config.model.fallback.slot_5_label",
] as const;

const ITEMS_PER_PAGE = 25;
const FALLBACK_DEBUG_ENABLED = new Set(["1", "true", "yes", "on"]).has(
	(process.env.FALLBACK_DEBUG_ENABLED ?? "").trim().toLowerCase(),
);

/**
 * Returns a localized description string for a given LLM model, with capability flags prepended.
 * Reuses the same format as the /config model text command for consistency.
 *
 * @param model - The LLM model row from the database
 * @param locale - User's preferred locale (e.g., "ja", "en-US")
 * @returns Localized description string with flags prefix
 */
function getLocalizedDescription(model: LlmRow, locale: string): string {
	const normalizedLocale = locale.toLowerCase().split("-")[0];
	const description =
		normalizedLocale === "ja" ? model.ja_description : model.llm_description;
	const baseDescription =
		description || model.llm_description || `${model.llm_provider} model`;

	if (model.llm_codename === "other-model") return baseDescription;

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
		.setName("fallback")
		.setDescription(
			localizer("en-US", "commands.config.model.fallback.description"),
		);

/**
 * Handles the /config model fallback command.
 * Allows server admins to configure up to 5 ordered fallback models for automatic failover.
 *
 * @param _client - Discord client instance (unused)
 * @param interaction - The slash command interaction
 * @param userData - Invoking user's database record
 * @param locale - User's preferred locale
 */
export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	// 1a. Scope modal custom ID to this invocation so stale awaitModalSubmit listeners
	//     from earlier (un-submitted) runs don't also resolve on this submission.
	const MODAL_CUSTOM_ID = `config_model_fallback_modal_${interaction.id}`;

	// 1b. Ensure the command is run in a channel context
	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	// 2. Load the Tomori state for this server
	const serverDiscId = interaction.guild?.id ?? interaction.user.id;
	const tomoriState = await getCachedTomoriState(serverDiscId);
	if (!tomoriState) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.tomori_not_setup_title",
			descriptionKey: "general.errors.tomori_not_setup_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}
	if (FALLBACK_DEBUG_ENABLED) {
		log.info(
			`[FallbackDebug][/config model fallback] server_disc_id=${serverDiscId} server_id=${tomoriState.server_id} current_fallbacks=[${(tomoriState.fallback_llms ?? []).map((llm) => `${llm.llm_id}:${llm.llm_codename}`).join(", ")}]`,
		);
	}

	// 3. Block custom providers — model names are free-text, no enumerated list to select from
	const currentProvider = tomoriState.llm.llm_provider.toLowerCase();
	if (currentProvider === "custom") {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.config.model.fallback.custom_provider_title",
			descriptionKey:
				"commands.config.model.fallback.custom_provider_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 4. Load available models for the current provider
	const availableModels = await loadAvailableModelsForProvider(currentProvider);
	if (!availableModels || availableModels.length === 0) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.config.model.fallback.no_models_title",
			descriptionKey: "commands.config.model.fallback.no_models_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 5. Build select options from available models
	const allModelOptions: SelectOption[] = availableModels.map((m) => ({
		label: safeSelectOptionText(m.llm_codename),
		value: safeSelectOptionText(m.llm_codename),
		description: safeSelectOptionText(
			getLocalizedDescription(m, userData.language_pref),
		),
	}));

	// 6. Handle pagination when models exceed Discord's 25-option limit per select
	let optionsForModal = allModelOptions;
	let modalInteraction: ChatInputCommandInteraction | ButtonInteraction =
		interaction;

	if (allModelOptions.length > ITEMS_PER_PAGE) {
		const totalPages = Math.ceil(allModelOptions.length / ITEMS_PER_PAGE);

		// 6a. Build page-selection embed with numbered buttons
		const pageSelectEmbed = createStandardEmbed(locale, {
			titleKey: "general.pagination.select_page_title",
			descriptionKey: "general.pagination.select_page_description",
			descriptionVars: {
				totalItems: allModelOptions.length,
				totalPages,
			},
			color: ColorCode.INFO,
		});

		const maxButtons = Math.min(totalPages, 9);
		const pageButtons = Array.from({ length: maxButtons }, (_, i) =>
			new ButtonBuilder()
				.setCustomId(`fallback_page_${i + 1}`)
				.setLabel((i + 1).toString())
				.setStyle(ButtonStyle.Primary),
		);

		const actionRow = new ActionRowBuilder<ButtonBuilder>().addComponents(
			...pageButtons,
		);

		// 6b. Reply with page selector (first acknowledgment for this interaction)
		const pageSelectMessage = await interaction.reply({
			embeds: [pageSelectEmbed],
			components: [actionRow],
			flags: MessageFlags.Ephemeral,
		});

		try {
			// 6c. Wait for user to select a page
			const pageButtonInteraction =
				await pageSelectMessage.awaitMessageComponent({
					filter: (i) =>
						i.user.id === interaction.user.id &&
						i.customId.startsWith("fallback_page_"),
					time: 300_000,
				});

			// 6d. Slice the options to the selected page
			const selectedPage = Number.parseInt(
				pageButtonInteraction.customId.replace("fallback_page_", ""),
				10,
			);
			const startIndex = (selectedPage - 1) * ITEMS_PER_PAGE;
			const endIndex = Math.min(
				startIndex + ITEMS_PER_PAGE,
				allModelOptions.length,
			);
			optionsForModal = allModelOptions.slice(startIndex, endIndex);
			modalInteraction = pageButtonInteraction as ButtonInteraction;
		} catch {
			// Timeout — user did not select a page; clean up and exit
			await interaction
				.editReply({ embeds: [], components: [] })
				.catch(() => {});
			return;
		}
	}

	// 7. Show modal with 5 select fields (one per fallback slot)
	// autoDeferReply: MessageFlags.Ephemeral ensures the submit interaction is pre-deferred
	const modalResult = await promptWithRawModal(
		modalInteraction,
		locale,
		{
			modalCustomId: MODAL_CUSTOM_ID,
			modalTitleKey: "commands.config.model.fallback.modal_title",
			components: SLOT_IDS.map((customId, index) => ({
				customId,
				labelKey: SLOT_LABEL_KEYS[index],
				placeholder: localizer(
					locale,
					"commands.config.model.fallback.select_placeholder",
				),
				required: index === 0, // Only slot 1 is required
				options: optionsForModal,
			})),
		},
		MessageFlags.Ephemeral,
	);

	if (modalResult.outcome !== "submit") {
		log.info(
			`Fallback model modal ${modalResult.outcome} for user ${userData.user_id}`,
		);
		return;
	}

	if (!modalResult.interaction || !modalResult.values) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	const modalSubmitInteraction = modalResult.interaction;
	const values = modalResult.values;

	// 8. Collect non-empty slot values in order
	const rawSlots = SLOT_IDS.map((id) => (values[id] ?? "").trim()).filter(
		(v) => v !== "",
	);

	// 9. Deduplicate while preserving order (silently drop later duplicates)
	const seen = new Set<string>();
	const deduplicatedCodenames: string[] = [];
	for (const codename of rawSlots) {
		if (!seen.has(codename)) {
			seen.add(codename);
			deduplicatedCodenames.push(codename);
		}
	}

	// 10. Validate: no fallback can duplicate the primary model
	const primaryCodename = tomoriState.llm.llm_codename;
	if (deduplicatedCodenames.some((c) => c === primaryCodename)) {
		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "commands.config.model.fallback.primary_conflict_title",
			descriptionKey:
				"commands.config.model.fallback.primary_conflict_description",
			descriptionVars: { model: primaryCodename },
			color: ColorCode.ERROR,
		});
		return;
	}

	// 11. Resolve codenames to llm_id values (invalid codenames are silently skipped)
	const resolvedIds: number[] = [];
	const resolvedCodenames: string[] = [];
	for (const codename of deduplicatedCodenames) {
		const match = availableModels.find((m) => m.llm_codename === codename);
		if (match?.llm_id !== undefined) {
			resolvedIds.push(match.llm_id);
			resolvedCodenames.push(codename);
		}
	}
	if (FALLBACK_DEBUG_ENABLED) {
		log.info(
			`[FallbackDebug][/config model fallback] server_disc_id=${serverDiscId} selected_slots=[${rawSlots.join(", ")}] deduplicated=[${deduplicatedCodenames.join(", ")}] resolved_ids=[${resolvedIds.join(", ")}]`,
		);
	}

	// 12. Write to database
	const writeOk = await setFallbackLlms(tomoriState.server_id, resolvedIds);
	if (FALLBACK_DEBUG_ENABLED) {
		log.info(
			`[FallbackDebug][/config model fallback] server_disc_id=${serverDiscId} server_id=${tomoriState.server_id} write_ok=${writeOk}`,
		);
	}
	if (!writeOk) {
		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "general.errors.update_failed_title",
			descriptionKey: "general.errors.update_failed_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	// 13. Invalidate cache so the next generation uses the new fallback chain
	invalidateTomoriStateCache(serverDiscId);

	// 14. Success embed
	if (resolvedIds.length === 0) {
		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "commands.config.model.fallback.cleared_title",
			descriptionKey: "commands.config.model.fallback.cleared_description",
			color: ColorCode.SUCCESS,
		});
	} else {
		const modelList = resolvedCodenames
			.map((c, i) => `${i + 1}. \`${c}\``)
			.join("\n");
		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "commands.config.model.fallback.success_title",
			descriptionKey: "commands.config.model.fallback.success_description",
			descriptionVars: { model_list: modelList },
			color: ColorCode.SUCCESS,
		});
	}
}
