import {
	MessageFlags,
	type ButtonInteraction,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import { invalidateTomoriStateCache } from "@/utils/cache/tomoriStateCache";
import { loadAllPersonasForServer } from "@/utils/db/dbRead";
import { updateTomori } from "@/utils/db/dbWrite";
import {
	promptWithPaginatedModal,
	replyInfoEmbed,
	replyPaginatedPersonaChoicesV2,
	safeSelectOptionText,
} from "@/utils/discord/interactionHelper";
import { ColorCode, log } from "@/utils/misc/logger";
import { getOptApiKey } from "@/utils/security/crypto";
import type { ModalResult, SelectOption } from "@/types/discord/modal";
import type {
	ErrorContext,
	TomoriState,
	UserRow,
} from "@/types/db/schema";
import { localizer } from "@/utils/text/localizer";
import {
	ELEVENLABS_SERVICE_NAME,
} from "@/utils/audio/elevenLabsAccount";
import {
	type ElevenLabsVoiceCatalogEntry,
	fetchElevenLabsVoiceCatalog,
} from "@/utils/audio/elevenLabsVoiceCatalog";

const VOICE_SELECT_MODAL_ID = "config_voice_elevenlabs_modal";
const VOICE_SELECT_ID = "voice_select";
const CLEAR_VOICE_VALUE = "__clear__";

function buildVoiceDescription(
	voice: ElevenLabsVoiceCatalogEntry,
	locale: string,
): string {
	const summaryParts = [
		voice.category,
		voice.labels.gender,
		voice.labels.age,
		voice.labels.accent,
	]
		.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
		.map((value) => value.trim());

	if (summaryParts.length > 0) {
		return safeSelectOptionText(summaryParts.join(" | "));
	}

	if (voice.description) {
		return safeSelectOptionText(voice.description);
	}

	return safeSelectOptionText(
		localizer(locale, "commands.config.voice.elevenlabs.voice_available_description"),
	);
}

function buildVoiceOptions(
	voices: ElevenLabsVoiceCatalogEntry[],
	locale: string,
): SelectOption[] {
	const clearOption: SelectOption = {
		label: safeSelectOptionText(
			localizer(locale, "commands.config.voice.elevenlabs.clear_choice_label"),
		),
		value: CLEAR_VOICE_VALUE,
		description: safeSelectOptionText(
			localizer(
				locale,
				"commands.config.voice.elevenlabs.clear_choice_description",
			),
		),
	};

	return [
		clearOption,
		...voices.map((voice) => ({
			label: safeSelectOptionText(voice.name),
			value: voice.voiceId,
			description: buildVoiceDescription(voice, locale),
		})),
	];
}

export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("elevenlabs")
		.setDescription(
			localizer("en-US", "commands.config.voice.elevenlabs.description"),
		);

export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	const serverDiscId = interaction.guild?.id ?? interaction.user.id;
	let selectedPersona: TomoriState | null = null;
	let modalResult: ModalResult | null = null;

	if (!interaction.channel) {
		await replyInfoEmbed(interaction, userData.language_pref, {
			titleKey: "general.errors.channel_only_title",
			descriptionKey: "general.errors.channel_only_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	try {
		const allPersonas = await loadAllPersonasForServer(serverDiscId);
		if (allPersonas.length === 0) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.tomori_not_setup_title",
				descriptionKey: "general.errors.tomori_not_setup_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		const serverId = allPersonas[0]?.server_id;
		if (!serverId) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "general.errors.tomori_not_setup_title",
				descriptionKey: "general.errors.tomori_not_setup_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		const apiKey = await getOptApiKey(serverId, ELEVENLABS_SERVICE_NAME);
		if (!apiKey) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.config.voice.elevenlabs.no_key_title",
				descriptionKey: "commands.config.voice.elevenlabs.no_key_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		const voiceCatalogResult = await fetchElevenLabsVoiceCatalog(apiKey);
		if (!voiceCatalogResult.success) {
			log.warn(
				`Failed to fetch ElevenLabs voice catalog for server ${serverId}: ${voiceCatalogResult.details ?? voiceCatalogResult.errorKind ?? "unknown"}`,
			);
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.config.voice.elevenlabs.voice_fetch_failed_title",
				descriptionKey:
					"commands.config.voice.elevenlabs.voice_fetch_failed_description",
				color: ColorCode.ERROR,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		const availableVoices = voiceCatalogResult.voices ?? [];
		if (availableVoices.length === 0) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.config.voice.elevenlabs.no_voices_title",
				descriptionKey: "commands.config.voice.elevenlabs.no_voices_description",
				color: ColorCode.WARN,
				flags: MessageFlags.Ephemeral,
			});
			return;
		}

		while (true) {
			const personaSelection = await replyPaginatedPersonaChoicesV2(
				interaction,
				locale,
				{
					personas: allPersonas,
					color: ColorCode.INFO,
					preserveSelectedInteraction: true,
					titleKey: "commands.config.voice.elevenlabs.select_persona_title",
					onSelect: async () => {},
				},
			);
			if (!personaSelection.success) {
				if (personaSelection.reason !== "cancelled") continue;
				return;
			}
			if (
				personaSelection.selectedIndex === undefined ||
				!personaSelection.interaction
			) {
				return;
			}

			const personaButtonInteraction = personaSelection.interaction as ButtonInteraction;
			selectedPersona = allPersonas[personaSelection.selectedIndex] ?? null;
			if (!selectedPersona?.tomori_id) {
				await replyInfoEmbed(personaButtonInteraction, locale, {
					titleKey: "general.errors.invalid_option_title",
					descriptionKey: "general.errors.invalid_option_description",
					color: ColorCode.ERROR,
				});
				return;
			}

			modalResult = await promptWithPaginatedModal(
				personaButtonInteraction,
				locale,
				{
					modalCustomId: VOICE_SELECT_MODAL_ID,
					modalTitleKey: "commands.config.voice.elevenlabs.modal_title",
					components: [
						{
							customId: VOICE_SELECT_ID,
							labelKey: "commands.config.voice.elevenlabs.select_label",
							descriptionKey:
								"commands.config.voice.elevenlabs.select_description",
							placeholder:
								"commands.config.voice.elevenlabs.select_placeholder",
							required: true,
							options: buildVoiceOptions(availableVoices, locale),
						},
					],
				},
			);
			if (modalResult.outcome !== "submit" || !modalResult.interaction) {
				continue;
			}

			const modalInteraction = modalResult.interaction;
			const selectedVoiceId = modalResult.values?.[VOICE_SELECT_ID];
			if (!selectedVoiceId) {
				await replyInfoEmbed(modalInteraction, locale, {
					titleKey: "general.errors.invalid_option_title",
					descriptionKey: "general.errors.invalid_option_description",
					color: ColorCode.ERROR,
				});
				return;
			}

			const nextVoice =
				selectedVoiceId === CLEAR_VOICE_VALUE
					? null
					: (availableVoices.find((voice) => voice.voiceId === selectedVoiceId) ??
						null);
			if (selectedVoiceId !== CLEAR_VOICE_VALUE && !nextVoice) {
				await replyInfoEmbed(modalInteraction, locale, {
					titleKey: "general.errors.invalid_option_title",
					descriptionKey: "general.errors.invalid_option_description",
					color: ColorCode.ERROR,
				});
				return;
			}

			const updatedTomori = await updateTomori(selectedPersona.tomori_id, {
				elevenlabs_voice_id: nextVoice?.voiceId ?? null,
				elevenlabs_voice_name: nextVoice?.name ?? null,
			});
			if (!updatedTomori) {
				await replyInfoEmbed(modalInteraction, locale, {
					titleKey: "general.errors.update_failed_title",
					descriptionKey: "general.errors.update_failed_description",
					color: ColorCode.ERROR,
				});
				return;
			}

			invalidateTomoriStateCache(serverDiscId);

			await replyInfoEmbed(modalInteraction, locale, {
				titleKey:
					nextVoice === null
						? "commands.config.voice.elevenlabs.cleared_title"
						: "commands.config.voice.elevenlabs.success_title",
				descriptionKey:
					nextVoice === null
						? "commands.config.voice.elevenlabs.cleared_description"
						: "commands.config.voice.elevenlabs.success_description",
				descriptionVars:
					nextVoice === null
						? {
								persona: selectedPersona.tomori_nickname,
							}
						: {
								persona: selectedPersona.tomori_nickname,
								voice: nextVoice.name,
							},
				color: ColorCode.SUCCESS,
			});
			break;
		}
	} catch (error) {
		const errorReplyInteraction = modalResult?.interaction ?? interaction;
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: selectedPersona?.server_id ?? null,
			tomoriId: selectedPersona?.tomori_id ?? null,
			errorType: "CommandExecutionError",
			metadata: {
				command: "config voice elevenlabs",
				guildId: interaction.guild?.id ?? interaction.user.id,
				executorDiscordId: interaction.user.id,
				selectedPersonaId: selectedPersona?.tomori_id ?? null,
			},
		};
		await log.error(
			`Error executing /config voice elevenlabs for user ${userData.user_disc_id}`,
			error as Error,
			context,
		);

		await replyInfoEmbed(errorReplyInteraction, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
	}
}
