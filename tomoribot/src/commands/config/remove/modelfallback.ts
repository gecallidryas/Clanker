/**
 * /config remove modelfallback
 * Removes one or more models from the server's fallback chain.
 * Presents checkbox groups of all configured fallbacks and drops the unchecked ones.
 */

import {
	EmbedBuilder,
	MessageFlags,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import {
	replyInfoEmbed,
	promptWithRawModal,
} from "@/utils/discord/interactionHelper";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "@/utils/cache/tomoriStateCache";
import { setFallbackLlms } from "@/utils/db/dbWrite";
import type { UserRow, ErrorContext, LlmRow } from "@/types/db/schema";
import type { CheckboxGroupOption } from "@/types/discord/modal";

// ─── Constants ────────────────────────────────────────────────────────────────

// Note: MODAL_CUSTOM_ID is generated per-invocation (see execute()) to prevent stale
// awaitModalSubmit listeners from a previous run resolving on the same submission.
const FALLBACK_CHECKBOX_ID = "fallback_checkbox_group";
const FALLBACK_DEBUG_ENABLED = new Set(["1", "true", "yes", "on"]).has(
	(process.env.FALLBACK_DEBUG_ENABLED ?? "").trim().toLowerCase(),
);

// ─── Subcommand Configuration ─────────────────────────────────────────────────

/**
 * Configures the 'modelfallback' subcommand for /config remove.
 */
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("modelfallback")
		.setDescription(
			localizer("en-US", "commands.config.remove.modelfallback.description"),
		);

// ─── Execute ──────────────────────────────────────────────────────────────────

/**
 * Executes the /config remove modelfallback command.
 * Flow:
 *   1. Load TomoriState and read the current fallback_llms chain
 *   2. If empty, reply with "none configured"
 *   3. Show checkbox groups with each fallback slot pre-checked
 *   4. Remove unchecked entries and write the remaining list back in order
 *
 * @param _client - Discord client instance
 * @param interaction - Slash command interaction
 * @param userData - Invoking user's data
 * @param locale - User's preferred locale
 */
export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	// 0. Scope modal custom ID to this invocation — prevents stale awaitModalSubmit
	//    listeners from a prior (un-submitted) run resolving on this submission.
	const MODAL_CUSTOM_ID = `config_remove_modelfallback_modal_${interaction.id}`;

	// 1. Ensure command is run in a guild
	if (!interaction.guild) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.guild_only_title",
			descriptionKey: "general.errors.guild_only_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// NOTE: No deferReply here — promptWithRawModal must be the first
	// acknowledgment. Pre-modal checks are cache-backed and complete within 3 seconds.

	try {
		// 2. Load TomoriState to get fallback chain and server_id
		const serverDiscId = interaction.guild.id;
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
				`[FallbackDebug][/config remove modelfallback] server_disc_id=${serverDiscId} server_id=${tomoriState.server_id} current_fallbacks=[${(tomoriState.fallback_llms ?? []).map((llm) => `${llm.llm_id}:${llm.llm_codename}`).join(", ")}]`,
			);
		}

		// 3. Check there are fallbacks to remove
		const currentFallbacks = tomoriState.fallback_llms ?? [];
		if (currentFallbacks.length === 0) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.config.remove.modelfallback.none_title",
				descriptionKey:
					"commands.config.remove.modelfallback.none_description",
				color: ColorCode.WARN,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		// 4. Show modal — first interaction acknowledgment
		const modalResult = await promptWithRawModal(
			interaction,
			locale,
			{
				modalCustomId: MODAL_CUSTOM_ID,
				modalTitleKey: "commands.config.remove.modelfallback.modal_title",
				components: [
					{
						kind: "checkboxGroup",
						customId: FALLBACK_CHECKBOX_ID,
						labelKey:
							"commands.config.remove.modelfallback.checkbox_label",
						descriptionKey:
							"commands.config.remove.modelfallback.checkbox_description",
						minValues: 0,
						required: false,
						options: buildFallbackOptions(currentFallbacks),
					},
				],
			},
			MessageFlags.Ephemeral,
		);

		if (modalResult.outcome !== "submit") return;

		if (!modalResult.interaction) {
			log.error("Fallback removal modal unexpectedly missing interaction");
			return;
		}
		const modalInteraction = modalResult.interaction;

		// 5. Resolve checked and unchecked fallback entries
		const checkedIndices = new Set<number>();
		for (const index of modalResult.multiValues?.[FALLBACK_CHECKBOX_ID] ?? []) {
			checkedIndices.add(Number.parseInt(index, 10));
		}

		const remainingFallbacks = currentFallbacks.filter((_, index) =>
			checkedIndices.has(index),
		);
		const removedFallbacks = currentFallbacks.filter(
			(_, index) => !checkedIndices.has(index),
		);
		if (FALLBACK_DEBUG_ENABLED) {
			log.info(
				`[FallbackDebug][/config remove modelfallback] server_disc_id=${serverDiscId} checked_indices=[${Array.from(checkedIndices).join(", ")}] removed=[${removedFallbacks.map((llm) => llm.llm_codename).join(", ")}]`,
			);
		}

		if (removedFallbacks.length === 0) {
			await replyInfoEmbed(modalInteraction, locale, {
				titleKey: "commands.config.remove.modelfallback.no_removals_title",
				descriptionKey:
					"commands.config.remove.modelfallback.no_removals_description",
				color: ColorCode.INFO,
			});
			return;
		}

		// 6. Build the new chain without the unchecked entries, preserving order
		const remainingIds = remainingFallbacks
			.map((llm) => llm.llm_id)
			.filter((id): id is number => id !== undefined);

		// 7. Write the updated chain to the database
		const writeOk = await setFallbackLlms(tomoriState.server_id, remainingIds);
		if (FALLBACK_DEBUG_ENABLED) {
			log.info(
				`[FallbackDebug][/config remove modelfallback] server_disc_id=${serverDiscId} server_id=${tomoriState.server_id} remaining_ids=[${remainingIds.join(", ")}] write_ok=${writeOk}`,
			);
		}
		if (!writeOk) {
			const context: ErrorContext = {
				serverId: tomoriState.server_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					operation: "setFallbackLlms",
					removedCodenames: removedFallbacks.map((llm) => llm.llm_codename),
					remainingIds,
				},
			};
			await log.error(
				"Failed to update fallback LLM chain after removal",
				new Error("setFallbackLlms returned false"),
				context,
			);
			await replyInfoEmbed(modalInteraction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 8. Invalidate cache so next generation uses the updated fallback chain
		invalidateTomoriStateCache(serverDiscId);

		// 9. Reply success
		await replyInfoEmbed(modalInteraction, locale, {
			titleKey: "commands.config.remove.modelfallback.success_title",
			descriptionKey: "commands.config.remove.modelfallback.success_description",
			descriptionVars: {
				models_removed: formatRemovedNames(
					removedFallbacks.map((llm) => `\`${llm.llm_codename}\``),
				),
				remaining_count: remainingIds.length,
			},
			color: ColorCode.SUCCESS,
		});

		log.success(
			`Removed ${removedFallbacks.length} fallback model(s) from server ${serverDiscId}. ` +
				`${remainingIds.length} fallback(s) remaining.`,
		);
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			errorType: "CommandExecutionError",
			metadata: { command: "config remove modelfallback" },
		};
		await log.error(
			"Error in /config remove modelfallback",
			error as Error,
			context,
		);

		if (!interaction.replied && !interaction.deferred) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.unknown_error_title",
				descriptionKey: "general.errors.unknown_error_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
		} else {
			await interaction.editReply({
				embeds: [
					new EmbedBuilder()
						.setTitle(
							localizer(locale, "general.errors.unknown_error_title"),
						)
						.setDescription(
							localizer(locale, "general.errors.unknown_error_description"),
						)
						.setColor(ColorCode.ERROR),
				],
			});
		}
	}
}

function buildFallbackOptions(currentFallbacks: LlmRow[]): CheckboxGroupOption[] {
	return currentFallbacks.map((llm, index) => ({
		value: index.toString(),
		label: `${index + 1}. ${llm.llm_codename}`,
		description: llm.llm_provider,
		default: true,
	}));
}

function formatRemovedNames(names: string[]): string {
	const maxVisibleNames = 10;
	const visibleNames = names.slice(0, maxVisibleNames);
	const suffix = names.length > maxVisibleNames ? ", ..." : "";
	return `${visibleNames.join(", ")}${suffix}`;
}
