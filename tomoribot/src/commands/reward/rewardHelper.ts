import type { SlashCommandSubcommandBuilder } from "discord.js";
import type { ChatInputCommandInteraction, Client, Message } from "discord.js";
import { EmbedBuilder, MessageFlags, PermissionFlagsBits } from "discord.js";
import {
	promptWithPaginatedModal,
	replyInfoEmbed,
	safeSelectOptionText,
} from "../../utils/discord/interactionHelper";
import { ColorCode, log } from "../../utils/misc/logger";
import { localizer } from "../../utils/text/localizer";
import type { UserRow } from "../../types/db/schema";
import type { SelectOption } from "../../types/discord/modal";
import tomoriChat from "../../events/messageCreate/tomoriChat";
import {
	loadAllPersonasForServer,
	loadTomoriState,
} from "../../utils/db/dbRead";

/**
 * Creates a reward subcommand handler pair (configureSubcommand + execute).
 *
 * Each reward command shares identical flow — guild validation, persona selection,
 * embed display, and tomoriChat triggering — differing only in name and locale keys.
 *
 * Locale keys expected under `commands.reward.{rewardName}`:
 *   - `description` — slash command description
 *   - `embed_title` — embed title shown when the reward is given
 *   - `embed_description` — embed body, supports `{user}` and `{bot}` placeholders
 *
 * @param rewardName - Unique identifier for this reward (e.g. "headpat", "hug")
 * @returns Object with `configureSubcommand` and `execute` ready for command export
 */
export function createRewardCommand(rewardName: string) {
	/**
	 * Configure the reward subcommand with name and localized description
	 * @param subcommand - The slash command subcommand builder
	 * @returns The configured subcommand
	 */
	const configureSubcommand = (subcommand: SlashCommandSubcommandBuilder) =>
		subcommand
			.setName(rewardName)
			.setDescription(
				localizer("en-US", `commands.reward.${rewardName}.description`),
			);

	/**
	 * Execute the reward command — display embed and trigger a bot response
	 * @param client - Discord client instance
	 * @param interaction - Command interaction
	 * @param _userData - User data from database (not used)
	 * @param locale - Locale of the interaction
	 */
	async function execute(
		client: Client,
		interaction: ChatInputCommandInteraction,
		_userData: UserRow,
		locale: string,
	): Promise<void> {
		// 1. Ensure command is run in a guild text channel
		if (!interaction.channel || !("messages" in interaction.channel)) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.guild_only_title",
				descriptionKey: "general.errors.guild_only_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 2. Check if bot has required permissions to read message history
		const botMember = interaction.guild?.members.me;
		if (!botMember || !interaction.guild) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.unknown_error_title",
				descriptionKey: "general.errors.unknown_error_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// Get the guild channel — check both regular channels and threads
		const guildChannel =
			interaction.guild.channels.cache.get(interaction.channel.id) ??
			interaction.channel;

		// Verify it's a guild-based channel with permissions
		if (!("permissionsFor" in guildChannel)) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.unknown_error_title",
				descriptionKey: "general.errors.unknown_error_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const permissions = guildChannel.permissionsFor(botMember);
		if (
			!permissions?.has(PermissionFlagsBits.ViewChannel) ||
			!permissions?.has(PermissionFlagsBits.ReadMessageHistory)
		) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.bot.respond.missing_permissions_title",
				descriptionKey:
					"commands.bot.respond.missing_permissions_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		// 3. Load tomori state for this server
		const tomoriState = await loadTomoriState(interaction.guild.id);
		if (!tomoriState) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.unknown_error_title",
				descriptionKey: "general.errors.unknown_error_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		// 4. Load all personas and check if alters exist
		const allPersonas = await loadAllPersonasForServer(interaction.guild.id);
		const alterPersonas = allPersonas.filter((p) => p.is_alter);
		const mainPersona = allPersonas.find((p) => !p.is_alter);

		let selectedPersona = mainPersona;
		let replyInteraction:
			| ChatInputCommandInteraction
			| import("discord.js").ModalSubmitInteraction = interaction;

		// If alters exist, show persona selection modal
		if (alterPersonas.length > 0 && mainPersona) {
			const personaOptions: SelectOption[] = [
				{
					label: safeSelectOptionText(mainPersona.tomori_nickname),
					value: "0",
					description: localizer(
						locale,
						"commands.bot.respond.main_persona_description",
					),
				},
				...alterPersonas.map((persona, index) => ({
					label: safeSelectOptionText(persona.tomori_nickname),
					value: (index + 1).toString(),
					description: localizer(
						locale,
						"commands.bot.respond.alter_persona_description",
					),
				})),
			];

			const modalResult = await promptWithPaginatedModal(
				interaction,
				locale,
				{
					modalCustomId: `reward_${rewardName}_persona_select`,
					modalTitleKey: "commands.bot.respond.select_persona_title",
					components: [
						{
							customId: "persona_choice",
							labelKey:
								"commands.bot.respond.select_persona_label",
							placeholder:
								"commands.bot.respond.select_persona_placeholder",
							required: true,
							options: personaOptions,
						},
					],
				},
			);

			if (modalResult.outcome !== "submit") {
				log.info(
					`Reward ${rewardName} persona selection ${modalResult.outcome} for user ${interaction.user.id}`,
				);
				return;
			}

			if (modalResult.interaction) {
				replyInteraction = modalResult.interaction;
			}

			const selectedIndex = Number.parseInt(
				modalResult.values?.persona_choice ?? "0",
				10,
			);
			selectedPersona =
				selectedIndex === 0
					? mainPersona
					: alterPersonas[selectedIndex - 1];

			log.info(
				`User ${interaction.user.id} selected persona ${selectedPersona.tomori_nickname} (ID: ${selectedPersona.tomori_id}) for ${rewardName} reward`,
			);
		}

		try {
			const botName =
				selectedPersona?.tomori_nickname ??
				tomoriState.tomori_nickname ??
				process.env.DEFAULT_BOTNAME ??
				"Tomori";

			// 5. Build reward embed (always public)
			const rewardEmbed = new EmbedBuilder()
				.setTitle(
					localizer(
						locale,
						`commands.reward.${rewardName}.embed_title`,
					),
				)
				.setDescription(
					localizer(
						locale,
						`commands.reward.${rewardName}.embed_description`,
						{
							user: `<@${interaction.user.id}>`,
							bot: botName,
						},
					),
				)
				.setColor(ColorCode.AFFECTION);

			// 6. Send response (always public, suppress notifications)
			await replyInteraction.reply({
				embeds: [rewardEmbed],
				flags: MessageFlags.SuppressNotifications,
			});

			// 7. Get the latest message in the channel (includes the reward embed)
			const messages = await interaction.channel.messages.fetch({
				limit: 1,
			});
			const latestMessage = messages.first();

			if (!latestMessage) {
				log.warn(
					`No messages found in channel ${interaction.channel.id} for ${rewardName} reward command.`,
				);
				return;
			}

			// 8. Manually trigger tomoriChat (embed already injects reward context)
			log.info(
				`Reward ${rewardName} triggered by ${interaction.user.id} in channel ${interaction.channel.id} for message ${latestMessage.id}`,
			);

			await tomoriChat(
				client,
				latestMessage as Message,
				false, // isFromQueue
				true, // isManuallyTriggered
				undefined, // forceReason
				undefined, // reasoningQuery
				undefined, // llmOverrideCodename
				undefined, // isStopResponse
				0, // retryCount
				false, // skipLock
				undefined, // reminderRecipientID
				undefined, // reminderData
				selectedPersona?.tomori_id, // selectedPersonaId
				undefined, // isPersonaJob
				undefined, // isUserImpersonation
				undefined, // impersonatedUserId
				"user", // textQuotaSource
				interaction.id, // textQuotaTriggerKey
				interaction.user.id, // textQuotaUserDiscId
				undefined, // manualSystemPrompt
			);
		} catch (error) {
			log.error(`Error in reward ${rewardName} command:`, error, {
				errorType: `Reward${rewardName.charAt(0).toUpperCase() + rewardName.slice(1)}CommandError`,
				metadata: {
					userId: interaction.user.id,
					guildId: interaction.guild?.id ?? interaction.user.id,
					channelId: interaction.channel?.id,
				},
			});

			try {
				await replyInteraction.followUp({
					content: localizer(
						locale,
						"general.errors.unknown_error_description",
					),
					flags: MessageFlags.Ephemeral,
				});
			} catch (followUpError) {
				log.error(
					`Failed to send error followup for reward ${rewardName} command:`,
					followUpError,
				);
			}
		}
	}

	return { configureSubcommand, execute };
}
