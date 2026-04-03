import type {
	ButtonInteraction,
	ChatInputCommandInteraction,
	Client,
	Message,
} from "discord.js";
import {
	BaseGuildTextChannel,
	EmbedBuilder,
	MessageFlags,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import tomoriChat, {
	suppressNextSelfReply,
} from "@/events/messageCreate/tomoriChat";
import type { TomoriState, UserRow } from "@/types/db/schema";
import { isMatrixBridgeWebhookUsername } from "@/utils/bridge";
import {
	getCachedAllPersonas,
	getCachedMainPersona,
} from "@/utils/cache/tomoriStateCache";
import {
	replyInfoEmbed,
	replyPaginatedPersonaChoicesV2,
} from "@/utils/discord/interactionHelper";
import { normalizeMessageFetchLimit } from "@/utils/discord/messageFetchLimit";
import { ColorCode, log } from "@/utils/misc/logger";
import { localizer } from "@/utils/text/localizer";

/** Module-level lock set keyed by channelId — prevents double-invocation. */
const activeDeleteLocks = new Set<string>();

/**
 * Max message age (in ms) below which Discord allows bulk deletion.
 * Messages older than 14 days must be deleted individually.
 */
const BULK_DELETE_MAX_AGE_MS = 14 * 24 * 60 * 60 * 1000;

/**
 * Configures the 'turn' subcommand under the 'delete' group.
 * @param subcommand - SlashCommandSubcommandBuilder
 * @returns Configured builder
 */
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("turn")
		.setDescription(
			localizer("en-US", "commands.tool.delete.turn.description"),
		)
		.addBooleanOption((option) =>
			option
				.setName("regenerate")
				.setDescription(
					localizer(
						"en-US",
						"commands.tool.delete.turn.regenerate_description",
					),
				)
				.setRequired(false),
		)
		.addBooleanOption((option) =>
			option
				.setName("select_persona")
				.setDescription(
					localizer(
						"en-US",
						"commands.tool.delete.turn.select_persona_description",
					),
				)
				.setRequired(false),
		);

/**
 * Executes the `/tool delete turn` command.
 *
 * Walks the recent channel history, finds the last contiguous block of
 * messages sent by a single known persona (via webhook username or bot
 * non-webhook messages), deletes those messages, and optionally re-triggers
 * that persona with `tomoriChat`. Matrix bridge relay webhooks are treated
 * as user messages and stop block detection without being deleted.
 *
 * Interaction patterns used:
 * - Without `select_persona`: Pattern 2 — deferReply on the slash interaction.
 * - With `select_persona`:    Pattern 4 — paginated picker returns a
 *   ButtonInteraction which is then deferred.
 *
 * @param client - Discord client instance
 * @param interaction - ChatInputCommandInteraction
 * @param _userData - User row from database (unused)
 * @param locale - User's locale string
 */
export async function execute(
	client: Client,
	interaction: ChatInputCommandInteraction,
	_userData: UserRow,
	locale: string,
): Promise<void> {
	// 1. Validate guild + channel presence
	if (!interaction.guild || !interaction.channel) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.guild_only_title",
			descriptionKey: "general.errors.guild_only_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	const guildId = interaction.guild.id;
	const channelId = interaction.channelId;
	const channel = interaction.channel;
	const regenerate = interaction.options.getBoolean("regenerate") ?? false;
	const selectPersona =
		interaction.options.getBoolean("select_persona") ?? false;

	// 2. Load main persona state — needed for permission check and config values
	const tomoriState = await getCachedMainPersona(guildId);
	if (!tomoriState) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.tomori_not_setup_title",
			descriptionKey: "general.errors.tomori_not_setup_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	// 3. Permission check: requires ManageGuild OR use in a designated RP channel
	const hasManageGuild =
		interaction.memberPermissions?.has("ManageGuild") ?? false;
	const isRpChannel = tomoriState.config.rp_channel_ids.includes(channelId);
	if (!hasManageGuild && !isRpChannel) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.tool.delete.turn.no_permission_title",
			descriptionKey:
				"commands.tool.delete.turn.no_permission_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	// 4. Race-condition lock check — prevents double-invocation for the same channel
	if (activeDeleteLocks.has(channelId)) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.tool.delete.turn.already_running_title",
			descriptionKey:
				"commands.tool.delete.turn.already_running_description",
			color: ColorCode.WARN,
		});
		return;
	}

	// 5. Acquire lock before any async work
	activeDeleteLocks.add(channelId);

	// activeInteraction is mutable: starts as the slash interaction but may be
	// reassigned to the ButtonInteraction returned by the paginated picker.
	let activeInteraction: ChatInputCommandInteraction | ButtonInteraction =
		interaction;

	try {
		// 6. Load all personas and build a lookup map by lowercased nickname
		const allPersonas = await getCachedAllPersonas(guildId);
		const personaByNickname = new Map<string, TomoriState>(
			allPersonas.map((p) => [p.tomori_nickname.toLowerCase(), p]),
		);

		// Target persona tracking — null means auto-detect from message history
		let targetPersonaKey: string | null = null;
		let resolvedPersona: TomoriState | null = null;

		// 7. Persona selection (conditional) — Pattern 4 when select_persona=true
		if (selectPersona) {
			if (allPersonas.length === 0) {
				// No personas configured — nothing to select or auto-detect
				await replyInfoEmbed(interaction, locale, {
					titleKey:
						"commands.tool.delete.turn.no_persona_found_title",
					descriptionKey:
						"commands.tool.delete.turn.no_persona_found_description",
					color: ColorCode.WARN,
				});
				return;
			}

			// Show paginated picker; preserveSelectedInteraction=true so we can
			// defer on the returned ButtonInteraction ourselves (Pattern 4)
			const personaSelection = await replyPaginatedPersonaChoicesV2(
				interaction,
				locale,
				{
					personas: allPersonas,
					color: ColorCode.INFO,
					preserveSelectedInteraction: true,
					onSelect: async () => {},
				},
			);

			if (
				!personaSelection.success ||
				personaSelection.selectedIndex === undefined ||
				!personaSelection.interaction
			) {
				// Picker was cancelled or timed out — the picker already showed the
				// appropriate UI; just release the lock via finally and return.
				return;
			}

			const buttonInteraction: ButtonInteraction =
				personaSelection.interaction;

			// Switch the active interaction to the button so all subsequent
			// editReply calls target the correct interaction token
			activeInteraction = buttonInteraction;

			resolvedPersona =
				allPersonas[personaSelection.selectedIndex] ?? null;
			targetPersonaKey =
				resolvedPersona?.tomori_nickname.toLowerCase() ?? null;

			// Acknowledge the button interaction ephemerally before doing async work
			await buttonInteraction.deferReply({ flags: MessageFlags.Ephemeral });
		} else {
			// No persona selection — defer the original slash interaction (Pattern 2)
			await interaction.deferReply({ flags: MessageFlags.Ephemeral });
		}

		// 8. Fetch recent messages from the channel
		const fetchLimit = normalizeMessageFetchLimit(
			tomoriState.config.message_fetch_limit,
		);
		const fetched = await channel.messages.fetch({ limit: fetchLimit });

		// Discord returns messages newest-first; reverse to chronological order
		// so index 0 = oldest and the last index = newest
		const messages: Message[] = [...fetched.values()].reverse();

		// 9. Walk newest-to-oldest to find the last contiguous persona block
		const blockMessages: Message[] = [];

		for (let i = messages.length - 1; i >= 0; i--) {
			const msg = messages[i];
			if (!msg) continue;

			if (!msg.webhookId) {
				// Non-webhook message — check if it's the bot's own direct message,
				// which represents the main persona speaking without a webhook
				if (msg.author.id === client.user?.id) {
					const mainPersona = allPersonas.find((p) => !p.is_alter);
					if (mainPersona) {
						const mainKey = mainPersona.tomori_nickname.toLowerCase();
						if (targetPersonaKey === null) {
							// Auto-detect: claim this as the target persona
							targetPersonaKey = mainKey;
							resolvedPersona = mainPersona;
							blockMessages.push(msg);
							continue;
						} else if (targetPersonaKey === mainKey) {
							// Matches target — add to block
							blockMessages.push(msg);
							continue;
						}
					}
				}

				// Not a tracked persona message; stop if we already have a block
				if (blockMessages.length > 0) break;
				continue;
			}

			// Matrix bridge relay webhooks represent user messages forwarded from
			// Matrix — they are never persona messages and must stop block detection
			if (isMatrixBridgeWebhookUsername(msg.author.username)) {
				if (blockMessages.length > 0) break;
				continue;
			}

			// Persona webhook — look up by raw (lowercased) username directly
			const lookupKey = msg.author.username.toLowerCase();
			const matchedPersona = personaByNickname.get(lookupKey);

			if (!matchedPersona) {
				// Webhook exists but username doesn't match any known persona
				// (e.g. user impersonation, external bots) — treat as non-persona
				if (blockMessages.length > 0) break;
				continue;
			}

			if (targetPersonaKey === null) {
				// Auto-detect: first persona webhook found is our target
				targetPersonaKey = lookupKey;
				resolvedPersona = matchedPersona;
				blockMessages.push(msg);
			} else if (lookupKey === targetPersonaKey) {
				// Contiguous message from the same persona — add to block
				blockMessages.push(msg);
			} else if (blockMessages.length > 0) {
				// A different persona appeared after we already collected target
				// messages — the contiguous block has ended
				break;
			}
			// else: different persona but target not yet found — keep scanning
			// backwards (handles select_persona where newer personas sit between
			// the command invocation and the target's last block)
		}

		// 10. No persona block found in recent history
		if (blockMessages.length === 0) {
			await activeInteraction.editReply({
				embeds: [
					new EmbedBuilder()
						.setTitle(
							localizer(
								locale,
								"commands.tool.delete.turn.no_persona_found_title",
							),
						)
						.setDescription(
							localizer(
								locale,
								"commands.tool.delete.turn.no_persona_found_description",
							),
						)
						.setColor(ColorCode.WARN),
				],
			});
			return;
		}

		const displayName =
			resolvedPersona?.tomori_nickname ?? targetPersonaKey ?? "Unknown";
		const totalCount = blockMessages.length;

		// 11. Inform user that deletion is in progress
		await activeInteraction.editReply({
			embeds: [
				new EmbedBuilder()
					.setTitle(
						localizer(
							locale,
							"commands.tool.delete.turn.deleting_title",
						),
					)
					.setDescription(
						localizer(
							locale,
							"commands.tool.delete.turn.deleting_description",
							{
								count: String(totalCount),
								persona_name: displayName,
							},
						),
					)
					.setColor(ColorCode.INFO),
			],
		});

		// 12. Partition messages into bulk-deletable (< 14 days) and old (≥ 14 days)
		const now = Date.now();
		const recentIds: string[] = [];
		const oldMessages: Message[] = [];

		for (const msg of blockMessages) {
			if (now - msg.createdTimestamp < BULK_DELETE_MAX_AGE_MS) {
				recentIds.push(msg.id);
			} else {
				oldMessages.push(msg);
			}
		}

		let deletedCount = 0;

		// 12a. Bulk-delete recent messages — Discord requires ≥ 2 IDs for bulkDelete
		if (recentIds.length >= 2 && channel instanceof BaseGuildTextChannel) {
			try {
				await channel.bulkDelete(recentIds);
				deletedCount += recentIds.length;
			} catch (bulkError) {
				log.warn(
					`[deleteTurn] bulkDelete failed for channelId=${channelId} — falling back to individual deletion`,
					bulkError,
				);
				// Fall back to individual deletion if bulk fails
				for (const id of recentIds) {
					try {
						const msg = fetched.get(id);
						if (msg) {
							await msg.delete();
							deletedCount++;
						}
					} catch (indivError) {
						log.warn(
							`[deleteTurn] Failed to individually delete messageId=${id}`,
							indivError,
						);
					}
				}
			}
		} else {
			// Single recent message OR thread channel — delete individually
			for (const id of recentIds) {
				try {
					const msg = fetched.get(id);
					if (msg) {
						await msg.delete();
						deletedCount++;
					}
				} catch (singleError) {
					log.warn(
						`[deleteTurn] Failed to delete messageId=${id}`,
						singleError,
					);
				}
			}
		}

		// 12b. Delete old messages individually (bulk-delete not allowed > 14 days)
		for (const msg of oldMessages) {
			try {
				await msg.delete();
				deletedCount++;
			} catch (oldError) {
				log.warn(
					`[deleteTurn] Failed to delete old messageId=${msg.id}`,
					oldError,
				);
			}
		}

		// 13. Build success / partial-success reply embed
		const isPartial = deletedCount < totalCount;
		const embedValues: Record<string, string> = {
			persona_name: displayName,
			count: String(deletedCount),
			deleted_count: String(deletedCount),
			total_count: String(totalCount),
		};

		let titleKey: string;
		let descKey: string;

		if (isPartial) {
			titleKey = "commands.tool.delete.turn.partial_title";
			descKey = "commands.tool.delete.turn.partial_description";
		} else if (regenerate && resolvedPersona) {
			titleKey = "commands.tool.delete.turn.success_title";
			descKey =
				"commands.tool.delete.turn.success_regenerate_description";
		} else {
			titleKey = "commands.tool.delete.turn.success_title";
			descKey = "commands.tool.delete.turn.success_description";
		}

		await activeInteraction.editReply({
			embeds: [
				new EmbedBuilder()
					.setTitle(localizer(locale, titleKey))
					.setDescription(localizer(locale, descKey, embedValues))
					.setColor(isPartial ? ColorCode.WARN : ColorCode.SUCCESS),
			],
		});

		log.info(
			`[deleteTurn] Deleted ${deletedCount}/${totalCount} messages from persona="${displayName}" in channelId=${channelId}`,
		);

		// 14. Regenerate (fire-and-forget) — re-trigger the persona after deletion
		if (regenerate && resolvedPersona && !isPartial) {
			try {
				// Fetch the most recent remaining message to use as the trigger context
				const remaining = await channel.messages.fetch({ limit: 1 });
				let lastMessage: Message | undefined = remaining.first();

				// If the channel has no messages left after deletion, seed a braille
				// blank placeholder so tomoriChat has a valid Message to operate on
				if (!lastMessage && channel instanceof BaseGuildTextChannel) {
					lastMessage = await channel.send("\u2800");
				}

				if (lastMessage) {
					// Prevent the self-reply suppression guard from blocking this trigger
					suppressNextSelfReply(channel.id);

					// Fire-and-forget — do not await so the command interaction resolves
					void tomoriChat(
						client,
						lastMessage,
						false, // isFromQueue
						true, // isManuallyTriggered
						false, // forceReason
						undefined, // reasoningQuery
						undefined, // llmOverrideCodename
						false, // isStopResponse
						0, // retryCount
						false, // skipLock
						undefined, // reminderRecipientID
						undefined, // reminderData
						resolvedPersona.tomori_id, // selectedPersonaId
						false, // isPersonaJob
						false, // isUserImpersonation
						undefined, // impersonatedUserId
						"user", // textQuotaSource
						interaction.id, // textQuotaTriggerKey
						interaction.user.id, // textQuotaUserDiscId
					);
				}
			} catch (regenError) {
				log.warn(
					`[deleteTurn] Failed to set up regenerate for persona="${displayName}"`,
					regenError,
				);
			}
		}
	} catch (error) {
		log.error(
			"[deleteTurn] Unexpected error during turn deletion",
			error,
			{
				errorType: "DeleteTurnError",
				metadata: {
					guildId: interaction.guildId,
					userId: interaction.user.id,
				},
			},
		);

		try {
			await activeInteraction.editReply({
				embeds: [
					new EmbedBuilder()
						.setTitle(
							localizer(locale, "general.errors.unexpected_title"),
						)
						.setDescription(
							localizer(
								locale,
								"general.errors.unexpected_description",
							),
						)
						.setColor(ColorCode.ERROR),
				],
			});
		} catch {
			// Interaction may have already expired — nothing we can do
		}
	} finally {
		// 15. Always release the channel lock regardless of outcome
		activeDeleteLocks.delete(channelId);
	}
}
