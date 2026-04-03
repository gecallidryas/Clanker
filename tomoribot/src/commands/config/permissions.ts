import {
	EmbedBuilder,
	MessageFlags,
	type ChatInputCommandInteraction,
	type Client,
	type ModalSubmitInteraction,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "../../utils/cache/tomoriStateCache";
import { localizer } from "../../utils/text/localizer";
import { log, ColorCode } from "../../utils/misc/logger";
import {
	replyInfoEmbed,
	promptWithRawModal,
} from "../../utils/discord/interactionHelper";
import {
	type UserRow,
	type ErrorContext,
	tomoriConfigSchema,
	type TomoriConfigRow,
} from "../../types/db/schema";
import { sql } from "@/utils/db/client";
import { hasOptApiKey } from "@/utils/security/crypto";
import { ELEVENLABS_SERVICE_NAME } from "@/utils/audio/elevenLabsAccount";
import type { CheckboxGroupOption } from "@/types/discord/modal";

// ─── Constants ────────────────────────────────────────────────────────────────

// Note: MODAL_CUSTOM_ID is generated per-invocation (see execute()) to prevent stale
// awaitModalSubmit listeners from a previous run resolving on the same submission.
const PERMISSIONS_CHECKBOX_ID = "config_permissions_checkbox";

// Rule 21: Configure the subcommand — no options needed, UI is a checkbox modal
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("permissions")
		.setDescription(
			localizer("en-US", "commands.config.permissions.description"),
		);

/**
 * Defines all configurable permissions for the checkbox modal.
 * Each entry maps a checkbox value to its DB column and locale keys.
 */
interface PermissionDefinition {
	/** Value used as the checkbox option identifier */
	value: string;
	/** The tomori_configs column to update */
	dbColumn: string;
	/** Locale key for the option label */
	labelKey: string;
	/** Locale key for the short option description shown in the checkbox */
	descKey: string;
	/** Extracts current state from a config row */
	getState: (config: TomoriConfigRow) => boolean;
	/** If true, this option is only shown when an ElevenLabs key is configured */
	requiresElevenLabs?: boolean;
}

const PERMISSION_DEFINITIONS: PermissionDefinition[] = [
	{
		value: "selfteaching",
		dbColumn: "self_teaching_enabled",
		labelKey: "commands.config.permissions.selfteaching_option",
		descKey: "commands.config.permissions.selfteaching_desc",
		getState: (c) => c.self_teaching_enabled,
	},
	{
		value: "personalization",
		dbColumn: "personal_memories_enabled",
		labelKey: "commands.config.permissions.personalization_option",
		descKey: "commands.config.permissions.personalization_desc",
		getState: (c) => c.personal_memories_enabled,
	},
	{
		value: "emojiusage",
		dbColumn: "emoji_usage_enabled",
		labelKey: "commands.config.permissions.emojiusage_option",
		descKey: "commands.config.permissions.emojiusage_desc",
		getState: (c) => c.emoji_usage_enabled,
	},
	{
		value: "stickerusage",
		dbColumn: "sticker_usage_enabled",
		labelKey: "commands.config.permissions.stickerusage_option",
		descKey: "commands.config.permissions.stickerusage_desc",
		getState: (c) => c.sticker_usage_enabled,
	},
	{
		value: "websearch",
		dbColumn: "web_search_enabled",
		labelKey: "commands.config.permissions.websearch_option",
		descKey: "commands.config.permissions.websearch_desc",
		getState: (c) => c.web_search_enabled,
	},
	{
		value: "pinmessage",
		dbColumn: "pin_message_enabled",
		labelKey: "commands.config.permissions.pinmessage_option",
		descKey: "commands.config.permissions.pinmessage_desc",
		getState: (c) => c.pin_message_enabled,
	},
	{
		value: "imagegen",
		dbColumn: "imagegen_enabled",
		labelKey: "commands.config.permissions.imagegen_option",
		descKey: "commands.config.permissions.imagegen_desc",
		getState: (c) => c.imagegen_enabled,
	},
	{
		value: "hiderespondembed",
		dbColumn: "hide_respond_embed",
		labelKey: "commands.config.permissions.hiderespondembed_option",
		descKey: "commands.config.permissions.hiderespondembed_desc",
		getState: (c) => c.hide_respond_embed,
	},
	{
		value: "hideimpersonationembeds",
		dbColumn: "hide_impersonation_embeds",
		labelKey: "commands.config.permissions.hideimpersonationembeds_option",
		descKey: "commands.config.permissions.hideimpersonationembeds_desc",
		getState: (c) => c.hide_impersonation_embeds,
	},
	{
		value: "voicemessage",
		dbColumn: "voice_message_enabled",
		labelKey: "commands.config.permissions.voicemessage_option",
		descKey: "commands.config.permissions.voicemessage_desc",
		getState: (c) => c.voice_message_enabled ?? true,
		requiresElevenLabs: true,
	},
];

/**
 * Configures various permissions for Tomori's behavior on the server using
 * a checkbox modal. Checked items = enabled.
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
	// 0. Scope modal custom ID to this invocation — prevents stale awaitModalSubmit
	//    listeners from a prior (un-submitted) run resolving on this submission.
	const MODAL_CUSTOM_ID = `config_permissions_modal_${interaction.id}`;

	// 1. Ensure command is run in a channel
	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	// NOTE: No deferReply here — promptWithRawModal must be the first
	// acknowledgment. Pre-modal checks are cache-backed and complete within 3 seconds.

	// Declared outside try/catch so the catch block can use the modal interaction
	// (which is auto-deferred) for error reporting instead of the consumed original interaction.
	let modalInteraction: ModalSubmitInteraction | null = null;

	try {
		// 2. Load the Tomori state for this server
		const guildKey = interaction.guild?.id ?? interaction.user.id;
		const tomoriState = await getCachedTomoriState(guildKey);
		if (!tomoriState) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.tomori_not_setup_title",
				descriptionKey: "general.errors.tomori_not_setup_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		// 3. Determine which permissions to show (voicemessage requires ElevenLabs key)
		let activeDefinitions = PERMISSION_DEFINITIONS;
		if (tomoriState.server_id) {
			const hasElevenLabsKey = await hasOptApiKey(
				tomoriState.server_id,
				ELEVENLABS_SERVICE_NAME,
			);
			if (!hasElevenLabsKey) {
				activeDefinitions = PERMISSION_DEFINITIONS.filter(
					(def) => !def.requiresElevenLabs,
				);
			}
		}

		// 4. Build checkbox options, pre-checking currently-enabled permissions
		const checkboxOptions: CheckboxGroupOption[] = activeDefinitions.map((def) => ({
			label: localizer(locale, def.labelKey),
			value: def.value,
			description: localizer(locale, def.descKey),
			default: def.getState(tomoriState.config),
		}));

		// 5. Show the checkbox modal — first interaction acknowledgment
		const modalResult = await promptWithRawModal(
			interaction,
			locale,
			{
				modalCustomId: MODAL_CUSTOM_ID,
				modalTitleKey: "commands.config.permissions.select_embed_title",
				components: [
					{
						kind: "checkboxGroup",
						customId: PERMISSIONS_CHECKBOX_ID,
						labelKey: "commands.config.permissions.select_placeholder",
						descriptionKey:
							"commands.config.permissions.select_embed_description",
						minValues: 0,
						required: false,
						options: checkboxOptions,
					},
				],
			},
			MessageFlags.Ephemeral,
		);

		if (modalResult.outcome !== "submit") return;

		if (!modalResult.interaction) {
			log.error("Permissions modal unexpectedly missing interaction");
			return;
		}
		modalInteraction = modalResult.interaction;

		// 6. Determine which permissions changed
		const newlyEnabled = new Set(
			modalResult.multiValues?.[PERMISSIONS_CHECKBOX_ID] ?? [],
		);
		const changes: Array<{ dbColumn: string; isEnabled: boolean; label: string }> =
			[];

		for (const def of activeDefinitions) {
			const wasEnabled = def.getState(tomoriState.config);
			const willBeEnabled = newlyEnabled.has(def.value);
			if (wasEnabled !== willBeEnabled) {
				changes.push({
					dbColumn: def.dbColumn,
					isEnabled: willBeEnabled,
					label: localizer(locale, def.labelKey),
				});
			}
		}

		// 7. If nothing changed, say so and exit
		if (changes.length === 0) {
			await replyInfoEmbed(modalInteraction, locale, {
				titleKey: "commands.config.permissions.no_changes_title",
				descriptionKey: "commands.config.permissions.no_changes_description",
				color: ColorCode.WARN,
			});
			return;
		}

		// 8. Apply each changed permission to the database.
		//    sql.unsafe is safe here: dbColumn values are strictly controlled by PERMISSION_DEFINITIONS.
		for (const change of changes) {
			const [updatedRow] = await sql`
				UPDATE tomori_configs
				SET ${sql.unsafe(change.dbColumn)} = ${change.isEnabled}
				WHERE server_id = ${tomoriState.server_id}
				RETURNING *
			`;

			const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);
			if (!validatedConfig.success || !updatedRow) {
				const context: ErrorContext = {
					tomoriId: tomoriState.tomori_id,
					serverId: tomoriState.server_id,
					userId: userData.user_id,
					errorType: "DatabaseUpdateError",
					metadata: {
						command: "config permissions",
						guildId: interaction.guild?.id ?? interaction.user.id,
						dbColumn: change.dbColumn,
						isEnabled: change.isEnabled,
						validationErrors: validatedConfig.success
							? null
							: validatedConfig.error.flatten(),
					},
				};
				await log.error(
					`Failed to update permission column: ${change.dbColumn}`,
					validatedConfig.success
						? new Error("Database update returned no rows")
						: new Error("Updated config failed validation"),
					context,
				);

				await replyInfoEmbed(modalInteraction, locale, {
					titleKey: "general.errors.update_failed_title",
					descriptionKey: "general.errors.update_failed_description",
					color: ColorCode.ERROR,
				});
				return;
			}
		}

		// 9. Invalidate cache so next message picks up the fresh config
		invalidateTomoriStateCache(guildKey);

		// 10. Build the success result embed listing what was enabled/disabled
		const enabledLabels = changes
			.filter((c) => c.isEnabled)
			.map((c) => `\`${c.label}\``);
		const disabledLabels = changes
			.filter((c) => !c.isEnabled)
			.map((c) => `\`${c.label}\``);

		let resultDescription = localizer(
			locale,
			"commands.config.permissions.success_description",
			{ count: changes.length },
		);
		if (enabledLabels.length > 0) {
			resultDescription += `\n✅ **Enabled:** ${enabledLabels.join(", ")}`;
		}
		if (disabledLabels.length > 0) {
			resultDescription += `\n🔴 **Disabled:** ${disabledLabels.join(", ")}`;
		}

		await modalInteraction.editReply({
			embeds: [
				new EmbedBuilder()
					.setTitle(
						localizer(locale, "commands.config.permissions.success_title"),
					)
					.setDescription(resultDescription)
					.setColor(ColorCode.SUCCESS),
			],
		});
	} catch (error) {
		// 11. Log the error with context
		let serverIdForError: number | null = null;
		let tomoriIdForError: number | null = null;
		if (interaction.guild?.id) {
			const state = await getCachedTomoriState(interaction.guild.id);
			serverIdForError = state?.server_id ?? null;
			tomoriIdForError = state?.tomori_id ?? null;
		}

		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: serverIdForError,
			tomoriId: tomoriIdForError,
			errorType: "CommandExecutionError",
			metadata: {
				command: "config permissions",
				guildId: interaction.guild?.id ?? interaction.user.id,
				executorDiscordId: interaction.user.id,
			},
		};
		await log.error(
			`Error executing /config permissions for user ${userData.user_disc_id}`,
			error as Error,
			context,
		);

		// 12. Inform user of unknown error
		// Use modalInteraction (auto-deferred) if available since the original
		// interaction is consumed by promptWithRawModal's raw REST acknowledgment.
		const activeInteraction = modalInteraction ?? interaction;
		await replyInfoEmbed(activeInteraction, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
	}
}
