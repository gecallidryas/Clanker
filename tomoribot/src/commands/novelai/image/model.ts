import type {
	ChatInputCommandInteraction,
	Client,
	ModalSubmitInteraction,
	SlashCommandSubcommandBuilder,
} from "discord.js";
import type { SelectOption } from "@/types/discord/modal";
import type { UserRow } from "@/types/db/schema";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "@/utils/cache/tomoriStateCache";
import { sql } from "@/utils/db/client";
import {
	promptWithRawModal,
	replyInfoEmbed,
	safeSelectOptionText,
} from "@/utils/discord/interactionHelper";
import {
	getDiffusionModelById,
	getLocalizedDiffusionModelDescription,
	getNovelAiDiffusionModels,
	resolveNaiDiffusionModel,
	type NaiDiffusionModelSource,
} from "@/utils/image/naiDiffusionModels";
import { ColorCode, log } from "@/utils/misc/logger";
import { localizer } from "@/utils/text/localizer";

const MODAL_CUSTOM_ID = "novelai_image_model_modal";
const MODEL_SELECT_ID = "nai_diffusion_model_id";
const AUTOMATIC_OPTION_VALUE = "automatic";

export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("model")
		.setDescription(
			localizer("en-US", "commands.novelai.image.model.description"),
		);

function appendDefaultSuffix(locale: string, label: string): string {
		return `${label}${localizer(
		locale,
		"commands.novelai.image.params.option_default_suffix",
	)}`;
}

function createModelOptions(
	locale: string,
	models: Awaited<ReturnType<typeof getNovelAiDiffusionModels>>,
): SelectOption[] {
	const automaticOption: SelectOption = {
		label: localizer(locale, "commands.novelai.image.model.automatic_label"),
		value: AUTOMATIC_OPTION_VALUE,
		description: localizer(
			locale,
			"commands.novelai.image.model.automatic_description",
		),
	};

	const modelOptions = models.map((model) => {
		const label = model.is_default
			? appendDefaultSuffix(locale, model.codename)
			: model.codename;

		return {
			label: safeSelectOptionText(label),
			value: model.diffusion_model_id.toString(),
			description: safeSelectOptionText(
				getLocalizedDiffusionModelDescription(model, locale),
			),
		};
	});

	return [automaticOption, ...modelOptions];
}

function getSourceLabelKey(source: NaiDiffusionModelSource): string {
	switch (source) {
		case "override":
			return "commands.novelai.image.model.source_override";
		case "shared":
			return "commands.novelai.image.model.source_shared";
		case "default":
			return "commands.novelai.image.model.source_default";
	}
}

export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	_userData: UserRow,
	locale: string,
): Promise<void> {
	if (!interaction.guild) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.guild_only_title",
			descriptionKey: "general.errors.guild_only_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	if (!interaction.memberPermissions?.has("ManageGuild")) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.permission_denied_title",
			descriptionKey: "general.errors.permission_denied_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	const tomoriState = await getCachedTomoriState(interaction.guild.id);
	if (!tomoriState) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.tomori_not_setup_title",
			descriptionKey: "general.errors.tomori_not_setup_description",
			color: ColorCode.ERROR,
		});
		return;
	}

	let modalSubmitInteraction: ModalSubmitInteraction | null = null;

	try {
		const [
			availableModels,
			currentOverrideModel,
			currentResolvedModel,
		] = await Promise.all([
			getNovelAiDiffusionModels(),
			tomoriState.config.nai_diffusion_model_id != null
				? getDiffusionModelById(tomoriState.config.nai_diffusion_model_id)
				: Promise.resolve(null),
			resolveNaiDiffusionModel(tomoriState.config),
		]);

		if (!availableModels.length) {
			await replyInfoEmbed(interaction, locale, {
				titleKey: "commands.novelai.image.model.no_models_title",
				descriptionKey: "commands.novelai.image.model.no_models_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const modalResult = await promptWithRawModal(interaction, locale, {
			modalCustomId: MODAL_CUSTOM_ID,
			modalTitleKey: "commands.novelai.image.model.modal_title",
			components: [
				{
					customId: MODEL_SELECT_ID,
					labelKey: "commands.novelai.image.model.select_label",
					descriptionKey: "commands.novelai.image.model.select_description",
					placeholder: currentOverrideModel?.provider === "novelai"
						? localizer(
								locale,
								"commands.novelai.image.model.select_placeholder_current_override",
								{
									model: currentOverrideModel.codename,
								},
							)
						: localizer(
								locale,
								"commands.novelai.image.model.select_placeholder_current_automatic",
								{
									model: currentResolvedModel.codename,
								},
							),
					required: true,
					options: createModelOptions(locale, availableModels),
				},
			],
		});

		if (modalResult.outcome !== "submit") {
			return;
		}

		// biome-ignore lint/style/noNonNullAssertion: submit outcome guarantees interaction exists
		const submitInteraction = modalResult.interaction!;
		modalSubmitInteraction = submitInteraction;

		const selectedValue = modalResult.values?.[MODEL_SELECT_ID]?.trim();
		if (!selectedValue) {
			await replyInfoEmbed(submitInteraction, locale, {
				titleKey: "commands.novelai.image.model.invalid_model_title",
				descriptionKey: "commands.novelai.image.model.invalid_model_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const nextOverrideModelId =
			selectedValue === AUTOMATIC_OPTION_VALUE
				? null
				: Number.parseInt(selectedValue, 10);

		if (
			selectedValue !== AUTOMATIC_OPTION_VALUE &&
			(Number.isNaN(nextOverrideModelId) || nextOverrideModelId == null)
		) {
			await replyInfoEmbed(submitInteraction, locale, {
				titleKey: "commands.novelai.image.model.invalid_model_title",
				descriptionKey: "commands.novelai.image.model.invalid_model_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		const selectedModel =
			nextOverrideModelId == null
				? null
				: (availableModels.find(
						(model) => model.diffusion_model_id === nextOverrideModelId,
					) ?? null);

		if (nextOverrideModelId != null && !selectedModel) {
			await replyInfoEmbed(submitInteraction, locale, {
				titleKey: "commands.novelai.image.model.invalid_model_title",
				descriptionKey: "commands.novelai.image.model.invalid_model_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		if (
			(nextOverrideModelId ?? null) ===
			(tomoriState.config.nai_diffusion_model_id ?? null)
		) {
			await replyInfoEmbed(submitInteraction, locale, {
				titleKey: "commands.novelai.image.model.already_selected_title",
				descriptionKey:
					"commands.novelai.image.model.already_selected_description",
				descriptionVars: {
					mode:
						selectedModel?.codename ??
						localizer(locale, "commands.novelai.image.model.automatic_label"),
				},
				color: ColorCode.WARN,
			});
			return;
		}

		const updated = await sql<Array<{ tomori_config_id: number }>>`
			UPDATE tomori_configs
			SET nai_diffusion_model_id = ${nextOverrideModelId}
			WHERE server_id = ${tomoriState.server_id}
			RETURNING tomori_config_id
		`;

		if (!updated.length) {
			await replyInfoEmbed(submitInteraction, locale, {
				titleKey: "general.errors.update_failed_title",
				descriptionKey: "general.errors.update_failed_description",
				color: ColorCode.ERROR,
			});
			return;
		}

		invalidateTomoriStateCache(interaction.guild.id);

		const resolvedModel = await resolveNaiDiffusionModel({
			diffusion_model_id: tomoriState.config.diffusion_model_id,
			nai_diffusion_model_id: nextOverrideModelId,
		});

		await replyInfoEmbed(submitInteraction, locale, {
			titleKey: "commands.novelai.image.model.success_title",
			descriptionKey: "commands.novelai.image.model.success_description",
			descriptionVars: {
				mode:
					selectedModel?.codename ??
					localizer(locale, "commands.novelai.image.model.automatic_label"),
				effective_model: resolvedModel.codename,
				source: localizer(locale, getSourceLabelKey(resolvedModel.source)),
			},
			color: ColorCode.SUCCESS,
		});
	} catch (error) {
		await log.error("Error in /novelai image model command", error, {
			errorType: "CommandExecutionError",
			metadata: {
				command: "novelai image model",
				guildId: interaction.guild.id,
				serverId: tomoriState.server_id,
				currentProvider: tomoriState.llm.llm_provider,
				currentDiffusionModelId: tomoriState.config.diffusion_model_id,
				currentNaiDiffusionModelId: tomoriState.config.nai_diffusion_model_id,
			},
		});

		await replyInfoEmbed(modalSubmitInteraction ?? interaction, locale, {
			titleKey: "general.errors.unknown_error_title",
			descriptionKey: "general.errors.unknown_error_description",
			color: ColorCode.ERROR,
		});
	}
}
