import {
	MessageFlags,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import { getCachedTomoriState } from "@/utils/cache/tomoriStateCache";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import { replyInfoEmbed } from "@/utils/discord/interactionHelper";
import { loadActivePreset, loadPresetsForServer, deletePreset } from "@/utils/db/stPresetDb";
import type { UserRow, ErrorContext } from "@/types/db/schema";

// ─── Subcommand Configuration ────────────────────────────────────────

/**
 * Configure the /stpreset remove subcommand.
 * No options — removes the currently active preset for the server.
 * @param subcommand - The subcommand builder
 */
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("remove")
		.setDescription(
			localizer("en-US", "commands.stpreset.remove.description"),
		);

// ─── Execution ───────────────────────────────────────────────────────

/**
 * Execute /stpreset remove.
 * Deletes the currently active SillyTavern preset for this server,
 * reverting the context builder to native fixed-block assembly.
 *
 * @param _client - Discord client instance
 * @param interaction - Command interaction
 * @param userData - User data from database
 * @param locale - User's preferred locale
 */
export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	// 1. Verify server setup
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

	try {
		// 2. Find the active preset, or fall back to the most recent preset for this server
		// Fallback handles the edge case where a preset was uploaded before activation logic existed
		let preset = await loadActivePreset(tomoriState.server_id);
		if (!preset) {
			const allPresets = await loadPresetsForServer(tomoriState.server_id);
			preset = allPresets[0] ?? null;
		}

		if (!preset || !preset.preset_id) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.stpreset.remove.no_preset_title",
				descriptionKey: "commands.stpreset.remove.no_preset_description",
				color: ColorCode.WARN,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		// 3. Delete the preset (cascade deletes nodes, invalidates cache)
		const deleted = await deletePreset(preset.preset_id, tomoriState.server_id);
		if (!deleted) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.stpreset.remove.failed_title",
				descriptionKey: "commands.stpreset.remove.failed_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		// 4. Confirm removal
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.stpreset.remove.success_title",
			descriptionKey: "commands.stpreset.remove.success_description",
			descriptionVars: { name: preset.preset_name },
			color: ColorCode.SUCCESS,
			flags: MessageFlags.Ephemeral,
		});

		log.info(
			`[ST Preset Remove] Deleted preset "${preset.preset_name}" (ID: ${preset.preset_id}) for server_id ${tomoriState.server_id}`,
		);
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: null,
			tomoriId: null,
			errorType: "CommandExecutionError",
			metadata: { command: "stpreset remove" },
		};
		await log.error("Error executing /stpreset remove", error as Error, context);

		await interaction.followUp({
			content: localizer(locale, "general.errors.unknown_error_description"),
			flags: MessageFlags.Ephemeral,
		});
	}
}
