import {
	MessageFlags,
	TextInputStyle,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import {
	loadUniqueProviders,
	loadDefaultModelForProvider,
	loadSavedProviderConfigs,
	getAllChannelLlmOverridesForServer,
	loadPersonaLlmOverridesForServer,
	loadLlmById,
} from "@/utils/db/dbRead";
import {
	clearAllChannelLlmOverridesForServer,
	clearAllPersonaLlmOverridesForServer,
	upsertSavedProviderConfig,
	restoreOverridesFromSnapshot,
	cleanupDeadChannelOverrides,
} from "@/utils/db/dbWrite";
import { invalidateAllChannelLlmCacheForServer } from "@/utils/cache/channelLlmCache";
import {
	getCachedTomoriState,
	invalidateTomoriStateCache,
} from "@/utils/cache/tomoriStateCache";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import {
	replyInfoEmbed,
	promptWithRawModal,
} from "@/utils/discord/interactionHelper";
import {
	type UserRow,
	type ErrorContext,
	tomoriConfigSchema,
	type SavedProviderConfigUpsert,
} from "@/types/db/schema";
import type { ProviderError } from "@/types/stream/interfaces";
import type {
	SelectOption,
	ModalComponent,
} from "@/types/discord/modal";
import { ProviderFactory } from "@/utils/provider/providerFactory";
import { getProviderDisplayName } from "@/utils/provider/providerInfoRegistry";
import { encryptApiKey } from "@/utils/security/crypto";
import { sql } from "@/utils/db/client";
import {
	isCustomProvider,
	promptCustomCapabilities,
	getCustomEndpointValidationMessage,
	CUSTOM_ENDPOINT_PLACEHOLDER_KEY,
	type CustomCapabilitiesResult,
} from "@/utils/discord/customProviderModal";
import { validateRemoteMcpUrl } from "@/utils/mcp/mcpUrlSecurity";
import { resolveLogitBiasEntriesForLlm } from "@/utils/provider/logitBiasResolver";

// Modal configuration constants
const MODAL_CUSTOM_ID = "config_provider_switch_modal";
const PROVIDER_SELECT_ID = "provider_select";
const API_KEY_INPUT_ID = "api_key_input";
const SAVE_CURRENT_SELECT_ID = "save_current_select";

// Configure the subcommand
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("switch")
		.setDescription(
			localizer("en-US", "commands.config.provider.switch.description"),
		);

/**
 * Switches AI provider with automatic config save/restore.
 * Saves the current provider config before switching (opt-out),
 * and restores saved configs when returning to a previously-used provider.
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

	// 3. Load unique providers and saved configs in parallel
	const [uniqueProviders, savedConfigs] = await Promise.all([
		loadUniqueProviders(),
		loadSavedProviderConfigs(tomoriState.server_id),
	]);

	if (!uniqueProviders || uniqueProviders.length === 0) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.config.apikey.set.no_providers_title",
			descriptionKey: "commands.config.apikey.set.no_providers_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 4. Build provider select options with "(saved)" indicator
	const savedProviderSet = new Set(
		savedConfigs.map((c) => c.provider.toLowerCase()),
	);
	const savedIndicator = localizer(
		locale,
		"commands.config.provider.switch.saved_indicator",
	);

	const providerSelectOptions: SelectOption[] = uniqueProviders.map(
		(provider) => {
			const isSaved = savedProviderSet.has(provider.toLowerCase());
			return {
				label: isSaved
					? `${getProviderDisplayName(provider)} ${savedIndicator}`
					: getProviderDisplayName(provider),
				value: provider.toLowerCase(),
				description: undefined,
			};
		},
	);

	// (save_current_select migrated to Checkbox in Phase 5 — no options array needed)

	// Track modal submit interaction for error handling in catch block
	let modalSubmitInteraction:
		| import("discord.js").ModalSubmitInteraction
		| undefined;

	try {
		// 6. Show modal with provider selection, optional API key, and save toggle
		const modalComponents: ModalComponent[] = [
			{
				customId: PROVIDER_SELECT_ID,
				labelKey: "commands.config.provider.switch.provider_label",
				descriptionKey:
					"commands.config.provider.switch.provider_description",
				placeholder: "commands.config.provider.switch.provider_placeholder",
				required: true,
				options: providerSelectOptions,
			},
			{
				customId: API_KEY_INPUT_ID,
				labelKey: "commands.config.provider.switch.api_key_label",
				descriptionKey: "commands.config.provider.switch.api_key_description_with_custom",
				placeholder: "commands.config.provider.switch.api_key_placeholder",
				required: false,
				style: TextInputStyle.Short,
				maxLength: 200,
			},
			{
				// Checkbox: checked (default) = save current config, unchecked = skip.
				// "true" (checked) or "false" (unchecked) in modalResult.values[SAVE_CURRENT_SELECT_ID].
				kind: "checkbox" as const,
				customId: SAVE_CURRENT_SELECT_ID,
				labelKey: "commands.config.provider.switch.save_current_label",
				descriptionKey:
					"commands.config.provider.switch.save_current_description",
				default: true,
			},
		];

		const modalResult = await promptWithRawModal(
			interaction,
			locale,
			{
				modalCustomId: MODAL_CUSTOM_ID,
				modalTitleKey: "commands.config.provider.switch.modal_title",
				components: modalComponents,
			},
			MessageFlags.Ephemeral,
		);

		// 7. Handle modal outcome
		if (modalResult.outcome !== "submit") {
			log.info(
				`Provider switch modal ${modalResult.outcome} for user ${userData.user_id}`,
			);
			return;
		}

		modalSubmitInteraction = modalResult.interaction;
		const selectedProvider = modalResult.values?.[PROVIDER_SELECT_ID];
		const apiKeyInput = modalResult.values?.[API_KEY_INPUT_ID]?.trim() || null;
		// Checkbox returns "true" (checked) or "false" (unchecked); default is "true" (pre-checked)
		const saveCurrentChoice =
			modalResult.values?.[SAVE_CURRENT_SELECT_ID] ?? "true";

		if (!modalSubmitInteraction || !selectedProvider) {
			log.error(
				"Provider switch modal result unexpectedly missing interaction or values",
			);
			return;
		}

		const normalizedProvider = selectedProvider.toLowerCase();
		const currentProvider = tomoriState.llm.llm_provider.toLowerCase();
		const isSameProvider = currentProvider === normalizedProvider;

		// 8. Save current config if requested (and there's an API key to save)
		// Also snapshot current channel/persona LLM overrides for later restoration
		if (saveCurrentChoice === "true" && !isSameProvider && tomoriState.config.api_key) {
			// Load current overrides to include in snapshot
			const [currentChannelOverrides, currentPersonaOverrides] =
				await Promise.all([
					getAllChannelLlmOverridesForServer(tomoriState.server_id),
					loadPersonaLlmOverridesForServer(tomoriState.server_id),
				]);

			const currentConfig: SavedProviderConfigUpsert = {
				server_id: tomoriState.server_id,
				provider: currentProvider,
				api_key: tomoriState.config.api_key,
				key_version: tomoriState.config.key_version ?? 1,
				llm_id: tomoriState.config.llm_id,
				diffusion_model_id: tomoriState.config.diffusion_model_id ?? null,
				embedding_model_id: tomoriState.config.embedding_model_id ?? null,
				nai_diffusion_model_id:
					tomoriState.config.nai_diffusion_model_id ?? null,
				vision_llm_id: tomoriState.config.vision_llm_id ?? null,
				nai_preset_name: tomoriState.config.nai_preset_name ?? null,
				custom_endpoint_url: tomoriState.config.custom_endpoint_url ?? null,
				custom_model_name: tomoriState.config.custom_model_name ?? null,
				fallback_llm_ids: tomoriState.config.fallback_llm_ids ?? [],
				// Snapshot sampler/parameter settings
				llm_temperature: tomoriState.config.llm_temperature,
				llm_top_p: tomoriState.config.llm_top_p,
				llm_top_k: tomoriState.config.llm_top_k,
				llm_frequency_penalty: tomoriState.config.llm_frequency_penalty,
				llm_presence_penalty: tomoriState.config.llm_presence_penalty,
				llm_min_p: tomoriState.config.llm_min_p,
				llm_logit_biases: tomoriState.config.llm_logit_biases ?? [],
				channel_llm_overrides: currentChannelOverrides
					.filter((o): o is typeof o & { llm: { llm_id: number } } =>
						o.llm.llm_id != null,
					)
					.map((o) => ({
						channel_disc_id: o.channelDiscId,
						llm_id: o.llm.llm_id,
					})),
				persona_llm_overrides: currentPersonaOverrides,
			};

			const saved = await upsertSavedProviderConfig(
				tomoriState.server_id,
				currentConfig,
			);
			if (saved) {
				log.info(
					`Saved current provider config for ${currentProvider} (with ${currentChannelOverrides.length} channel + ${currentPersonaOverrides.length} persona overrides) before switching to ${normalizedProvider}`,
				);
			} else {
				log.warn(
					`Failed to save current provider config for ${currentProvider} — continuing with switch`,
				);
			}
		}

		// 9. Resolve new config: check for saved config for target provider
		// Use already-loaded savedConfigs array instead of a second DB query
		const savedConfig =
			savedConfigs.find(
				(c) => c.provider.toLowerCase() === normalizedProvider,
			) ?? null;
		const hasApiKeyInput = apiKeyInput !== null && apiKeyInput.length > 0;
		const isRestoringFromSaved = savedConfig !== null && !hasApiKeyInput;

		// 10. Handle Custom Provider vs Regular Provider
		let encrypted: Buffer;
		let version: number;
		let customCapabilitiesResult: CustomCapabilitiesResult | null = null;
		let customEndpointUrl: string | null = null;
		let customModelName: string | null = null;
		let newLlmId = tomoriState.config.llm_id;
		let newDiffusionModelId = tomoriState.config.diffusion_model_id;
		let newEmbeddingModelId = tomoriState.config.embedding_model_id;
		let newNaiDiffusionModelId = tomoriState.config.nai_diffusion_model_id;
		let newVisionLlmId = tomoriState.config.vision_llm_id;
		let newNaiPresetName = tomoriState.config.nai_preset_name;
		let newFallbackLlmIds: number[] = tomoriState.config.fallback_llm_ids ?? [];
		// Sampler/parameter settings to carry over (null = keep current values)
		let newTemperature: number | null = null;
		let newTopP: number | null = null;
		let newTopK: number | null = null;
		let newFrequencyPenalty: number | null = null;
		let newPresencePenalty: number | null = null;
		let newMinP: number | null = null;
		let newLogitBiasEntries = tomoriState.config.llm_logit_biases ?? [];

		if (isRestoringFromSaved) {
			// Restoring from saved config — use saved values
			// Guard: saved config must have a non-null API key to restore
			if (!savedConfig.api_key) {
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey:
						"commands.config.provider.switch.first_time_no_key_title",
					descriptionKey:
						"commands.config.provider.switch.first_time_no_key_description",
					descriptionVars: {
						provider: getProviderDisplayName(normalizedProvider),
					},
					color: ColorCode.ERROR,
				});
				return;
			}

			log.info(
				`Restoring saved config for provider ${normalizedProvider}, server ${tomoriState.server_id}`,
			);

			encrypted = savedConfig.api_key;
			version = savedConfig.key_version;
			customEndpointUrl = savedConfig.custom_endpoint_url;
			customModelName = savedConfig.custom_model_name;
			// Restore sampler settings from snapshot
			newTemperature = savedConfig.llm_temperature ?? null;
			newTopP = savedConfig.llm_top_p ?? null;
			newTopK = savedConfig.llm_top_k ?? null;
			newFrequencyPenalty = savedConfig.llm_frequency_penalty ?? null;
			newPresencePenalty = savedConfig.llm_presence_penalty ?? null;
			newMinP = savedConfig.llm_min_p ?? null;
			newLogitBiasEntries = savedConfig.llm_logit_biases ?? [];

			if (isCustomProvider(normalizedProvider)) {
				if (!customEndpointUrl) {
					await replyInfoEmbed(modalSubmitInteraction, locale, {
						titleKey: "commands.config.custom.endpoint_url_invalid_title",
						descriptionKey: "commands.config.custom.endpoint_url_invalid_description",
						color: ColorCode.ERROR,
					});
					return;
				}
				const savedUrlValidation = await validateRemoteMcpUrl(customEndpointUrl);
				if (!savedUrlValidation.valid) {
					const validationMessage = getCustomEndpointValidationMessage(savedUrlValidation);
					await replyInfoEmbed(modalSubmitInteraction, locale, {
						titleKey: "commands.config.custom.endpoint_url_invalid_title",
						descriptionKey: validationMessage.descriptionKey,
						descriptionVars: validationMessage.descriptionVars,
						color: ColorCode.ERROR,
					});
					return;
				}

				// Saved custom configs can lose llm_id because the historical cleanup path
				// deleted the server-scoped custom llm row and the FK nulls this snapshot.
				// Rebuild the custom llm entry on demand so the active provider truly becomes custom.
				if (savedConfig.llm_id) {
					newLlmId = savedConfig.llm_id;
				} else {
					log.warn(
						`Saved custom provider config for server ${tomoriState.server_id} is missing llm_id; prompting capabilities to rebuild custom model entry`,
					);

					customCapabilitiesResult = await promptCustomCapabilities(
						modalSubmitInteraction,
						locale,
						serverId,
					);

					if (
						!customCapabilitiesResult.success ||
						!customCapabilitiesResult.llmId
					) {
						await replyInfoEmbed(modalSubmitInteraction, locale, {
							titleKey: "general.errors.operation_failed_title",
							description:
								customCapabilitiesResult.error ||
								localizer(
									locale,
									"commands.config.custom.capabilities_timeout",
								),
							color: ColorCode.ERROR,
						});
						return;
					}

					newLlmId = customCapabilitiesResult.llmId;
					customModelName = customCapabilitiesResult.modelName || customModelName;
				}

				newDiffusionModelId = null;
				newEmbeddingModelId = null;
				newNaiDiffusionModelId = null;
				newVisionLlmId = null;
				newNaiPresetName = null;
				newFallbackLlmIds = [];
			} else {
				newLlmId = savedConfig.llm_id ?? newLlmId;
				newDiffusionModelId = savedConfig.diffusion_model_id;
				newEmbeddingModelId = savedConfig.embedding_model_id;
				newNaiDiffusionModelId = savedConfig.nai_diffusion_model_id;
				newVisionLlmId = savedConfig.vision_llm_id ?? null;
				newNaiPresetName = savedConfig.nai_preset_name;
				newFallbackLlmIds = savedConfig.fallback_llm_ids ?? [];
			}
		} else if (isCustomProvider(normalizedProvider)) {
			// Custom provider flow: apiKeyInput contains the endpoint URL
			if (!hasApiKeyInput && !savedConfig) {
				// First-time custom with no URL
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey:
						"commands.config.provider.switch.first_time_no_key_title",
					descriptionKey:
						"commands.config.provider.switch.first_time_no_key_description",
					descriptionVars: {
						provider: getProviderDisplayName(normalizedProvider),
					},
					color: ColorCode.ERROR,
				});
				return;
			}

			// Use the provided endpoint URL, or fall back to saved one
			const endpointUrl = hasApiKeyInput
				? apiKeyInput
				: savedConfig?.custom_endpoint_url;

			const endpointUrlValidation = await validateRemoteMcpUrl(endpointUrl ?? "");
		if (!endpointUrl || !endpointUrlValidation.valid) {
				const validationMessage = endpointUrl
					? getCustomEndpointValidationMessage(endpointUrlValidation)
					: { descriptionKey: "commands.config.custom.endpoint_url_invalid_description" };
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey: "commands.config.custom.endpoint_url_invalid_title",
					descriptionKey: validationMessage.descriptionKey,
					descriptionVars: validationMessage.descriptionVars,
					color: ColorCode.ERROR,
				});
				return;
			}

			customEndpointUrl = endpointUrl;

			// Show capabilities modal for custom model configuration
			customCapabilitiesResult = await promptCustomCapabilities(
				modalSubmitInteraction,
				locale,
				serverId,
			);

			if (!customCapabilitiesResult.success) {
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey: "general.errors.operation_failed_title",
					description:
						customCapabilitiesResult.error ||
						localizer(
							locale,
							"commands.config.custom.capabilities_timeout",
						),
					color: ColorCode.ERROR,
				});
				return;
			}

			customModelName = customCapabilitiesResult.modelName || null;

			// Use placeholder API key for custom provider
			const placeholderResult = await encryptApiKey(
				CUSTOM_ENDPOINT_PLACEHOLDER_KEY,
			);
			encrypted = placeholderResult.encrypted;
			version = placeholderResult.version;

			if (customCapabilitiesResult.llmId) {
				newLlmId = customCapabilitiesResult.llmId;
			}
			newDiffusionModelId = null;
			newEmbeddingModelId = null;
			newNaiDiffusionModelId = null;
			newVisionLlmId = null;
			newNaiPresetName = null;
			newFallbackLlmIds = [];
		} else {
			// Regular provider flow
			if (!hasApiKeyInput && !savedConfig) {
				// First-time provider with no key
				await replyInfoEmbed(modalSubmitInteraction, locale, {
					titleKey:
						"commands.config.provider.switch.first_time_no_key_title",
					descriptionKey:
						"commands.config.provider.switch.first_time_no_key_description",
					descriptionVars: {
						provider: getProviderDisplayName(normalizedProvider),
					},
					color: ColorCode.ERROR,
				});
				return;
			}

			// Determine which API key to use: provided key overrides saved key
			const apiKeyToUse = hasApiKeyInput ? apiKeyInput : null;

			if (apiKeyToUse) {
				// Validate the new API key
				if (apiKeyToUse.length < 10) {
					await replyInfoEmbed(modalSubmitInteraction, locale, {
						titleKey: "commands.config.apikey.set.invalid_key_title",
						descriptionKey:
							"commands.config.apikey.set.invalid_key_description",
						color: ColorCode.ERROR,
					});
					return;
				}

				// Validate with provider
				let validationResult: { valid: boolean; error?: ProviderError } = {
					valid: false,
				};
				let providerInstance:
					| Awaited<ReturnType<typeof ProviderFactory.getProviderByName>>
					| undefined;

				try {
					providerInstance =
						await ProviderFactory.getProviderByName(normalizedProvider);
					validationResult =
						await providerInstance.validateApiKey(apiKeyToUse);
				} catch (error) {
					log.error(
						`Error validating API key for provider ${normalizedProvider}`,
						error as Error,
					);

					const errorMessage =
						error instanceof Error ? error.message : String(error);
					if (errorMessage.includes("Unsupported provider")) {
						await replyInfoEmbed(modalSubmitInteraction, locale, {
							titleKey:
								"commands.config.apikey.set.unsupported_provider_title",
							descriptionKey:
								"commands.config.apikey.set.unsupported_provider_description",
							descriptionVars: { provider: selectedProvider },
							color: ColorCode.ERROR,
						});
					} else {
						await replyInfoEmbed(modalSubmitInteraction, locale, {
							titleKey:
								"commands.config.apikey.set.validation_error_title",
							descriptionKey:
								"commands.config.apikey.set.validation_error_description",
							color: ColorCode.ERROR,
						});
					}
					return;
				}

				if (!validationResult.valid) {
					let errorDescription = "API key validation failed";
					if (validationResult.error) {
						try {
							if (providerInstance) {
								const formattedError =
									providerInstance.formatErrorDescription(
										validationResult.error,
										locale,
									);
								if (formattedError) {
									errorDescription = formattedError;
								}
							} else {
								errorDescription = `Error Code ${validationResult.error.code}: ${validationResult.error.message}`;
							}
						} catch {
							errorDescription = `Error Code ${validationResult.error.code}: ${validationResult.error.message}`;
						}
					}

					await replyInfoEmbed(modalSubmitInteraction, locale, {
						titleKey:
							"commands.config.apikey.set.key_validation_failed_title",
						description: errorDescription,
						color: ColorCode.ERROR,
					});
					return;
				}

				// Warm NovelAI subscription cache for new key
				if (
					normalizedProvider === "novelai" ||
					normalizedProvider === "nai"
				) {
					const guildIdForSubscription = interaction.guildId;
					if (guildIdForSubscription) {
						const { refreshNovelAISubscription: refreshNAISub } =
							await import(
								"../../../utils/cache/novelaiSubscriptionCache"
							);
						refreshNAISub(guildIdForSubscription, apiKeyToUse).catch(
							(err) => {
								log.warn(
									"Non-critical: failed to warm NovelAI subscription cache during provider switch",
									err,
								);
							},
						);
					}
				}

				// Encrypt the new key
				const encryptionResult = await encryptApiKey(apiKeyToUse);
				encrypted = encryptionResult.encrypted;
				version = encryptionResult.version;
			} else {
				// Use saved key (savedConfig is guaranteed non-null here from the
				// earlier guard that returns if both are missing)
				if (!savedConfig?.api_key) {
					await replyInfoEmbed(modalSubmitInteraction, locale, {
						titleKey:
							"commands.config.provider.switch.first_time_no_key_title",
						descriptionKey:
							"commands.config.provider.switch.first_time_no_key_description",
						descriptionVars: {
							provider: getProviderDisplayName(normalizedProvider),
						},
						color: ColorCode.ERROR,
					});
					return;
				}
				encrypted = savedConfig.api_key;
				version = savedConfig.key_version;
			}

			// If same provider, keep current models (only updating key)
			if (isSameProvider) {
				// Models stay the same; only key changes
			} else if (savedConfig && !hasApiKeyInput) {
				// Restoring saved models for this provider
				newLlmId = savedConfig.llm_id ?? newLlmId;
				newDiffusionModelId = savedConfig.diffusion_model_id;
				newEmbeddingModelId = savedConfig.embedding_model_id;
				newNaiDiffusionModelId = savedConfig.nai_diffusion_model_id;
				newVisionLlmId = savedConfig.vision_llm_id ?? null;
				newNaiPresetName = savedConfig.nai_preset_name;
				newFallbackLlmIds = savedConfig.fallback_llm_ids ?? [];
				// Restore sampler settings from snapshot
				newTemperature = savedConfig.llm_temperature ?? null;
				newTopP = savedConfig.llm_top_p ?? null;
				newTopK = savedConfig.llm_top_k ?? null;
				newFrequencyPenalty = savedConfig.llm_frequency_penalty ?? null;
				newPresencePenalty = savedConfig.llm_presence_penalty ?? null;
				newMinP = savedConfig.llm_min_p ?? null;
				newLogitBiasEntries = savedConfig.llm_logit_biases ?? [];
			} else {
				// Fresh provider switch — load default models
				const defaultModel =
					await loadDefaultModelForProvider(normalizedProvider);
				if (!defaultModel || !defaultModel.llm_id) {
					await replyInfoEmbed(modalSubmitInteraction, locale, {
						titleKey:
							"commands.config.apikey.set.no_default_model_title",
						descriptionKey:
							"commands.config.apikey.set.no_default_model_description",
						descriptionVars: {
							provider: getProviderDisplayName(normalizedProvider),
						},
						color: ColorCode.ERROR,
					});
					return;
				}

				newLlmId = defaultModel.llm_id;
				log.info(
					`Switching to default model for ${normalizedProvider}: ${defaultModel.llm_codename} (ID: ${newLlmId})`,
				);

				// Load default diffusion model
				const defaultDiffusionModel = (
					await sql`
						SELECT * FROM image_diffusion_models
						WHERE provider = ${normalizedProvider}
						  AND is_default = true
						  AND is_deprecated = false
						ORDER BY diffusion_model_id ASC
						LIMIT 1
					`
				)[0];

				if (!defaultDiffusionModel) {
					const fallbackDiffusionModel = (
						await sql`
							SELECT * FROM image_diffusion_models
							WHERE provider = ${normalizedProvider}
							  AND is_deprecated = false
							ORDER BY diffusion_model_id ASC
							LIMIT 1
						`
					)[0];

					newDiffusionModelId = fallbackDiffusionModel
						? fallbackDiffusionModel.diffusion_model_id
						: null;
				} else {
					newDiffusionModelId =
						defaultDiffusionModel.diffusion_model_id;
				}

				// Load default embedding model
				const defaultEmbeddingModel = (
					await sql`
						SELECT * FROM embedding_models
						WHERE provider = ${normalizedProvider}
						  AND is_default = true
						  AND is_deprecated = false
						ORDER BY embedding_model_id ASC
						LIMIT 1
					`
				)[0];

				if (!defaultEmbeddingModel) {
					const fallbackEmbeddingModel = (
						await sql`
							SELECT * FROM embedding_models
							WHERE provider = ${normalizedProvider}
							  AND is_deprecated = false
							ORDER BY embedding_model_id ASC
							LIMIT 1
						`
					)[0];

					newEmbeddingModelId = fallbackEmbeddingModel
						? fallbackEmbeddingModel.embedding_model_id
						: null;
				} else {
					newEmbeddingModelId =
						defaultEmbeddingModel.embedding_model_id;
				}

				// Reset provider-specific fields for fresh switch
				newNaiDiffusionModelId = null;
				newNaiPresetName = null;
				newFallbackLlmIds = [];
			}
		}

		// 11. Apply config to database
		const targetLlm =
			newLlmId === tomoriState.config.llm_id
				? tomoriState.llm
				: await loadLlmById(newLlmId);
		const resolvedLogitBiases = resolveLogitBiasEntriesForLlm(
			newLogitBiasEntries,
			targetLlm,
		);
		const newLogitBiasesJson = JSON.stringify(resolvedLogitBiases.entries);
		const [updatedRow] = await sql`
			UPDATE tomori_configs
			SET api_key = ${encrypted},
			    key_version = ${version},
			    llm_id = ${newLlmId},
			    diffusion_model_id = ${newDiffusionModelId},
			    embedding_model_id = ${newEmbeddingModelId},
			    nai_diffusion_model_id = ${newNaiDiffusionModelId},
			    vision_llm_id = ${newVisionLlmId},
			    nai_preset_name = ${newNaiPresetName},
			    custom_endpoint_url = ${customEndpointUrl},
			    custom_model_name = ${customModelName},
			    fallback_llm_ids = ${JSON.stringify(newFallbackLlmIds)}::jsonb,
			    llm_temperature = COALESCE(${newTemperature}, llm_temperature),
			    llm_top_p = COALESCE(${newTopP}, llm_top_p),
			    llm_top_k = COALESCE(${newTopK}, llm_top_k),
			    llm_frequency_penalty = COALESCE(${newFrequencyPenalty}, llm_frequency_penalty),
			    llm_presence_penalty = COALESCE(${newPresencePenalty}, llm_presence_penalty),
			    llm_min_p = COALESCE(${newMinP}, llm_min_p),
			    llm_logit_biases = ${newLogitBiasesJson}::jsonb
			WHERE server_id = ${tomoriState.server_id}
			RETURNING *
		`;

		// 13. Validate the returned data
		const validatedConfig = tomoriConfigSchema.safeParse(updatedRow);

		if (!validatedConfig.success || !updatedRow) {
			const context: ErrorContext = {
				tomoriId: tomoriState.tomori_id,
				serverId: tomoriState.server_id,
				userId: userData.user_id,
				errorType: "DatabaseUpdateError",
				metadata: {
					command: "config provider switch",
					selectedProvider,
					validationErrors: validatedConfig.success
						? null
						: validatedConfig.error.flatten(),
				},
			};
			await log.error(
				"Failed to update or validate config after provider switch",
				validatedConfig.success
					? new Error(
							"Database update returned no rows or unexpected data",
						)
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

		// 14. NovelAI auto-disable: when switching TO NovelAI for the first time
		// (not restoring a saved config), flip emoji and sticker usage off.
		// Runs BEFORE cache invalidation so a single invalidation covers both writes.
		if (
			!isSameProvider &&
			normalizedProvider === "novelai" &&
			!isRestoringFromSaved
		) {
			try {
				await sql`
					UPDATE tomori_configs
					SET emoji_usage_enabled = false,
					    sticker_usage_enabled = false
					WHERE server_id = ${tomoriState.server_id}
				`;
				log.info(
					`Auto-disabled emoji/sticker usage after switching to NovelAI for server ${tomoriState.server_id}`,
				);
			} catch (disableError) {
				log.warn(
					`Failed to auto-disable emoji/sticker for NovelAI switch: ${disableError}`,
				);
			}
		}

		// 14.1. On provider change, handle channel/persona overrides
		// Build valid channel ID set for dead override cleanup (guild channels only)
		const validChannelIds = new Set<string>();
		if (interaction.guild) {
			for (const [id] of interaction.guild.channels.cache) {
				validChannelIds.add(id);
			}
		}

		// Hoisted so the success message can reference restore counts
		let restoreResult: {
			channelRestored: number;
			personaRestored: number;
			skipped: number;
		} | null = null;

		if (!isSameProvider && isRestoringFromSaved) {
			// Restoring from saved config — clear current overrides, then restore saved ones
			// This replaces old-provider overrides with the saved snapshot for the target provider
			await clearAllChannelLlmOverridesForServer(tomoriState.server_id);
			await clearAllPersonaLlmOverridesForServer(tomoriState.server_id);

			const savedChannelOverrides = savedConfig?.channel_llm_overrides ?? [];
			const savedPersonaOverrides = savedConfig?.persona_llm_overrides ?? [];

			if (savedChannelOverrides.length > 0 || savedPersonaOverrides.length > 0) {
				restoreResult = await restoreOverridesFromSnapshot(
					tomoriState.server_id,
					savedChannelOverrides,
					savedPersonaOverrides,
					validChannelIds,
				);
				log.info(
					`Provider restore ${currentProvider}→${normalizedProvider}: ` +
						`${restoreResult.channelRestored} channel + ${restoreResult.personaRestored} persona overrides restored, ${restoreResult.skipped} skipped`,
				);
			}
		} else if (!isSameProvider) {
			// Fresh switch (no saved config) — clear all overrides
			const channelCleared = await clearAllChannelLlmOverridesForServer(
				tomoriState.server_id,
			);
			const personaCleared = await clearAllPersonaLlmOverridesForServer(
				tomoriState.server_id,
			);
			log.info(
				`Provider switch ${currentProvider}→${normalizedProvider}: ` +
					`channel overrides cleared=${channelCleared}, persona overrides cleared=${personaCleared}`,
			);
		}

		// 14.1.1. Dead override cleanup: remove channel overrides for deleted channels
		// Runs on every switch (including same-provider) as a lightweight maintenance pass
		if (interaction.guild && validChannelIds.size > 0) {
			const deadCleaned = await cleanupDeadChannelOverrides(
				tomoriState.server_id,
				validChannelIds,
			);
			if (deadCleaned > 0) {
				log.info(
					`Cleaned up ${deadCleaned} dead channel override(s) during provider switch`,
				);
			}
		}

		// 14.2. Invalidate caches AFTER all DB writes are complete
		invalidateTomoriStateCache(serverId);
		if (!isSameProvider) {
			invalidateAllChannelLlmCacheForServer(tomoriState.server_id);
		}

		// 14.3. Success message — always look up the active model by ID to handle
		// all cases correctly (same provider key update, restored config, fresh switch)
		const modelNameRow = (
			await sql`SELECT llm_codename FROM llms WHERE llm_id = ${newLlmId} LIMIT 1`
		)[0];
		const modelName =
			isCustomProvider(normalizedProvider) && customModelName?.trim()
				? customModelName.trim()
				: (modelNameRow?.llm_codename as string | undefined);

		const descriptionVars: Record<string, string> = {
			provider: getProviderDisplayName(normalizedProvider),
			model_name: modelName ?? "unknown",
		};

		// 15.1. Build restored config summary for the success embed
		// Lists which config categories were loaded back from the saved snapshot.
		// Settings not in the snapshot are silently carried over from the current config.
		if (isRestoringFromSaved && savedConfig) {
			// Split to avoid false positive in locale scanner ("commands.config" + ".provider.switch")
			const keyBase = "commands.config" + ".provider.switch";
			const restoredItems: string[] = [];
			const noRestoreItems: string[] = [];

			// Helper to push to the appropriate list
			const trackConfig = (hasData: boolean, label: string) => {
				if (hasData) {
					restoredItems.push(label);
				} else {
					noRestoreItems.push(label);
				}
			};

			// Chat Model
			trackConfig(!!savedConfig.llm_id, localizer(locale, `${keyBase}.config_label_chat_model`));

			// Vision Model
			trackConfig(!!savedConfig.vision_llm_id, localizer(locale, `${keyBase}.config_label_vision_model`));

			// Image Model (standard diffusion or NAI diffusion)
			trackConfig(
				!!(savedConfig.diffusion_model_id || savedConfig.nai_diffusion_model_id),
				localizer(locale, `${keyBase}.config_label_image_model`),
			);

			// Embedding Model
			trackConfig(!!savedConfig.embedding_model_id, localizer(locale, `${keyBase}.config_label_embedding_model`));

			// Sampler Settings — group all sampler fields as one category
			const hasSamplers = [
				savedConfig.llm_temperature,
				savedConfig.llm_top_p,
				savedConfig.llm_top_k,
				savedConfig.llm_frequency_penalty,
				savedConfig.llm_presence_penalty,
				savedConfig.llm_min_p,
			].some((v) => v != null);
			trackConfig(hasSamplers, localizer(locale, `${keyBase}.config_label_sampler_settings`));

			// Fallback Models (with count)
			const fallbackCount = savedConfig.fallback_llm_ids?.length ?? 0;
			if (fallbackCount > 0) {
				restoredItems.push(
					localizer(locale, `${keyBase}.config_label_fallback_models`, {
						count: fallbackCount,
					}),
				);
			} else {
				noRestoreItems.push(localizer(locale, `${keyBase}.config_label_fallback_models_none`));
			}

			// Channel Overrides (use actual restore counts if available)
			const channelRestoredCount = restoreResult?.channelRestored ?? 0;
			if (channelRestoredCount > 0) {
				restoredItems.push(
					localizer(locale, `${keyBase}.config_label_channel_overrides`, {
						count: channelRestoredCount,
					}),
				);
			} else {
				noRestoreItems.push(localizer(locale, `${keyBase}.config_label_channel_overrides_none`));
			}

			// Persona Overrides (use actual restore counts if available)
			const personaRestoredCount = restoreResult?.personaRestored ?? 0;
			if (personaRestoredCount > 0) {
				restoredItems.push(
					localizer(locale, `${keyBase}.config_label_persona_overrides`, {
						count: personaRestoredCount,
					}),
				);
			} else {
				noRestoreItems.push(localizer(locale, `${keyBase}.config_label_persona_overrides_none`));
			}

			// Custom Endpoint (only relevant for custom providers)
			trackConfig(!!savedConfig.custom_endpoint_url, localizer(locale, `${keyBase}.config_label_custom_endpoint`));

			// Build the details string — each section separated by a blank line
			let restoredDetails = "";
			if (restoredItems.length > 0) {
				restoredDetails += `\n\n✅ **${localizer(locale, `${keyBase}.restored_label`)}:** ${restoredItems.join(" · ")}`;
			}
			if (noRestoreItems.length > 0) {
				restoredDetails += `\n\n➖ **${localizer(locale, `${keyBase}.no_restores_label`)}:** ${noRestoreItems.join(" · ")}`;
			}
			// Static note: settings not in the snapshot keep their current values
			restoredDetails += `\n\n${localizer(locale, `${keyBase}.carried_over_note`)}`;

			// Note skipped overrides (channels/personas that no longer exist)
			const skippedCount = restoreResult?.skipped ?? 0;
			if (skippedCount > 0) {
				restoredDetails += `\n${localizer(locale, `${keyBase}.skipped_overrides_note`, { count: skippedCount })}`;
			}

			descriptionVars.restored_details = restoredDetails;
		}

		let successDescriptionKey: string;
		if (
			!isSameProvider &&
			normalizedProvider === "novelai" &&
			!isRestoringFromSaved
		) {
			successDescriptionKey =
				"commands.config.provider.switch.success_novelai_description";
		} else if (
			!isSameProvider &&
			(normalizedProvider === "zai" ||
				normalizedProvider === "zaicoding") &&
			!isRestoringFromSaved
		) {
			successDescriptionKey =
				"commands.config.provider.switch.success_zai_description";
		} else if (isRestoringFromSaved) {
			successDescriptionKey =
				"commands.config.provider.switch.success_restored_description";
		} else {
			successDescriptionKey =
				"commands.config.provider.switch.success_description";
		}

		await replyInfoEmbed(modalSubmitInteraction, locale, {
			titleKey: "commands.config.provider.switch.success_title",
			descriptionKey: successDescriptionKey,
			descriptionVars,
			color: ColorCode.SUCCESS,
		});
	} catch (error) {
		// Error handling
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
				command: "config provider switch",
				guildId: interaction.guild?.id,
				executorDiscordId: interaction.user.id,
			},
		};
		await log.error(
			`Error executing /config provider switch for user ${userData.user_disc_id}`,
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
