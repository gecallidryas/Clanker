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
  loadLlmById,
} from "../../../utils/db/dbRead";
import {
  clearAllChannelLlmOverridesForServer,
  clearAllPersonaLlmOverridesForServer,
} from "../../../utils/db/dbWrite";
import { invalidateAllChannelLlmCacheForServer } from "../../../utils/cache/channelLlmCache";
import {
  getCachedTomoriState,
  invalidateTomoriStateCache,
} from "../../../utils/cache/tomoriStateCache";
import { localizer } from "../../../utils/text/localizer";
import { log, ColorCode } from "../../../utils/misc/logger";
import {
  replyInfoEmbed,
  promptWithRawModal,
} from "../../../utils/discord/interactionHelper";
import {
  type UserRow,
  type ErrorContext,
  tomoriConfigSchema,
} from "../../../types/db/schema";
import type { ProviderError } from "../../../types/stream/interfaces";
import type {
  SelectOption,
  ModalComponent,
} from "../../../types/discord/modal";
import { ProviderFactory } from "../../../utils/provider/providerFactory";
import { getProviderDisplayName } from "@/utils/provider/providerInfoRegistry";
import { encryptApiKey } from "../../../utils/security/crypto";
import { sql } from "@/utils/db/client";
import {
  isCustomProvider,
  promptCustomCapabilities,
  getCustomEndpointValidationMessage,
  CUSTOM_ENDPOINT_PLACEHOLDER_KEY,
  type CustomCapabilitiesResult,
} from "../../../utils/discord/customProviderModal";
import { validateRemoteMcpUrl } from "@/utils/mcp/mcpUrlSecurity";
import { resolveLogitBiasEntriesForLlm } from "@/utils/provider/logitBiasResolver";

// Modal configuration constants
const MODAL_CUSTOM_ID = "config_apikeyset_modal";
const PROVIDER_SELECT_ID = "provider_select";
const API_KEY_INPUT_ID = "api_key_input";

// Configure the subcommand
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("set")
    .setDescription(
      localizer("en-US", "commands.config.apikey.set.description"),
    );

/**
 * Sets the API key Tomori will use for this server with dynamic provider selection
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
  // Use user ID for DM context, guild ID for server context
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

  // 3. Load unique providers from database
  const uniqueProviders = await loadUniqueProviders();
  if (!uniqueProviders || uniqueProviders.length === 0) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "commands.config.apikey.set.no_providers_title",
      descriptionKey: "commands.config.apikey.set.no_providers_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  // 4. Create provider select options with descriptions
  const providerSelectOptions: SelectOption[] = uniqueProviders.map(
    (provider) => ({
      label: getProviderDisplayName(provider),
      value: provider.toLowerCase(),
      description: undefined,
    }),
  );

  // Track modal submit interaction for error handling in catch block
  let modalSubmitInteraction:
    | import("discord.js").ModalSubmitInteraction
    | undefined;

  try {
    // 5. Show modal with provider selection and API key input
    const modalComponents: ModalComponent[] = [
      {
        customId: PROVIDER_SELECT_ID,
        labelKey: "commands.config.apikey.set.provider_label",
        descriptionKey: "commands.config.apikey.set.provider_description",
        placeholder: "commands.config.apikey.set.provider_placeholder",
        required: true,
        options: providerSelectOptions,
      },
      {
        customId: API_KEY_INPUT_ID,
        labelKey: "commands.config.apikey.set.api_key_label",
        // Show custom endpoint hint when not in production (custom provider available)
        descriptionKey:
          process.env.RUN_ENV !== "production"
            ? "commands.config.apikey.set.api_key_description_with_custom"
            : "commands.config.apikey.set.api_key_description",
        placeholder: "commands.config.apikey.set.api_key_placeholder",
        required: true,
        style: TextInputStyle.Short,
        maxLength: 200,
      },
    ];

    const modalResult = await promptWithRawModal(
      interaction,
      locale,
      {
        modalCustomId: MODAL_CUSTOM_ID,
        modalTitleKey: "commands.config.apikey.set.modal_title",
        components: modalComponents,
      },
      MessageFlags.Ephemeral, // Auto-defer with ephemeral flag
    );

    // 6. Handle modal outcome
    if (modalResult.outcome !== "submit") {
      log.info(
        `API key set modal ${modalResult.outcome} for user ${userData.user_id}`,
      );
      return;
    }

    // Extract values from the modal
    modalSubmitInteraction = modalResult.interaction;
    const selectedProvider = modalResult.values?.[PROVIDER_SELECT_ID];
    const apiKey = modalResult.values?.[API_KEY_INPUT_ID];

    // Safety checks
    if (!modalSubmitInteraction || !selectedProvider || !apiKey) {
      log.error("Modal result unexpectedly missing interaction or values");
      return;
    }

    // 7. Handle Custom Provider vs Regular Providers differently
    let encrypted: Buffer;
    let version: number;
    let customCapabilitiesResult: CustomCapabilitiesResult | null = null;
    let customEndpointUrl: string | null = null;
    const normalizedProvider = selectedProvider.toLowerCase();

    if (isCustomProvider(normalizedProvider)) {
      // Custom Provider Flow: apiKey field contains the endpoint URL
      log.info(`Custom provider selected - treating api_key as endpoint URL`);

      // Validate the endpoint URL format and security (blocks private IPs, localhost in prod, etc.)
      const urlValidation = await validateRemoteMcpUrl(apiKey ?? "");
      if (!apiKey || !urlValidation.valid) {
        const validationMessage = apiKey
          ? getCustomEndpointValidationMessage(urlValidation)
          : { descriptionKey: "commands.config.custom.endpoint_url_invalid_description" };
        await replyInfoEmbed(modalSubmitInteraction, locale, {
          titleKey: "commands.config.custom.endpoint_url_invalid_title",
          descriptionKey: validationMessage.descriptionKey,
          descriptionVars: validationMessage.descriptionVars,
          color: ColorCode.ERROR,
        });
        return;
      }

      customEndpointUrl = apiKey;
      log.info(`Custom endpoint URL validated: ${customEndpointUrl}`);

      // Show capabilities selection for custom model
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
            localizer(locale, "commands.config.custom.capabilities_timeout"),
          color: ColorCode.ERROR,
        });
        return;
      }

      log.info(
        `Custom model capabilities configured: tools=${customCapabilitiesResult.hasTools}, images=${customCapabilitiesResult.seesImages}, videos=${customCapabilitiesResult.seesVideos}, structOutput=${customCapabilitiesResult.supportsStructOutput}`,
      );

      // Use placeholder API key for custom provider
      const placeholderResult = await encryptApiKey(
        CUSTOM_ENDPOINT_PLACEHOLDER_KEY,
      );
      encrypted = placeholderResult.encrypted;
      version = placeholderResult.version;
    } else {
      // Regular Provider Flow
      // Basic API key validation - let helper functions manage interaction state
      if (apiKey.length < 10) {
        await replyInfoEmbed(modalSubmitInteraction, locale, {
          titleKey: "commands.config.apikey.set.invalid_key_title",
          descriptionKey: "commands.config.apikey.set.invalid_key_description",
          color: ColorCode.ERROR,
        });
        return;
      }

      // Get provider instance and validate API key using factory
      let validationResult: { valid: boolean; error?: ProviderError } = {
        valid: false,
      };
      let providerInstance:
        | Awaited<ReturnType<typeof ProviderFactory.getProviderByName>>
        | undefined;
      try {
        const providerName = selectedProvider.toLowerCase();

        // Use factory to get provider instance directly by canonical name or alias
        providerInstance = await ProviderFactory.getProviderByName(providerName);

        // Validate the API key with the provider
        validationResult = await providerInstance.validateApiKey(apiKey);
      } catch (error) {
        log.error(
          `Error validating API key for provider ${selectedProvider}`,
          error as Error,
        );

        // Check if error is due to unsupported provider
        const errorMessage =
          error instanceof Error ? error.message : String(error);
        if (errorMessage.includes("Unsupported provider")) {
          await replyInfoEmbed(modalSubmitInteraction, locale, {
            titleKey: "commands.config.apikey.set.unsupported_provider_title",
            descriptionKey:
              "commands.config.apikey.set.unsupported_provider_description",
            descriptionVars: {
              provider: selectedProvider,
            },
            color: ColorCode.ERROR,
          });
        } else {
          await replyInfoEmbed(modalSubmitInteraction, locale, {
            titleKey: "commands.config.apikey.set.validation_error_title",
            descriptionKey:
              "commands.config.apikey.set.validation_error_description",
            color: ColorCode.ERROR,
          });
        }
        return;
      }

      // Handle validation failure with detailed error information
      if (!validationResult.valid) {
        let errorDescription = "API key validation failed";

        if (validationResult.error) {
          try {
            if (providerInstance) {
              const formattedError = providerInstance.formatErrorDescription(
                validationResult.error,
                locale,
              );
              if (formattedError) {
                errorDescription = formattedError;
              }
            } else {
              errorDescription = `Error Code ${validationResult.error.code}: ${validationResult.error.message}`;
            }
          } catch (providerError) {
            log.warn(
              "Failed to format provider error description",
              providerError,
            );
            errorDescription = `Error Code ${validationResult.error.code}: ${validationResult.error.message}`;
          }
        }

        await replyInfoEmbed(modalSubmitInteraction, locale, {
          titleKey: "commands.config.apikey.set.key_validation_failed_title",
          description: errorDescription, // Use formatted error description
          color: ColorCode.ERROR,
        });
        return;
      }

      // For NovelAI: warm the subscription cache now (API key is plaintext here)
      // so the first message uses the correct tier context limit without an extra decrypt.
      if (normalizedProvider === "novelai" || normalizedProvider === "nai") {
        const guildIdForSubscription = interaction.guildId;
        if (guildIdForSubscription) {
          const { refreshNovelAISubscription: refreshNAISub } = await import(
            "../../../utils/cache/novelaiSubscriptionCache"
          );
          refreshNAISub(guildIdForSubscription, apiKey).catch((err) => {
            log.warn(
              "Non-critical: failed to warm NovelAI subscription cache during key set",
              err,
            );
          });
        }
      }

      // Encrypt and store the API key
      const encryptionResult = await encryptApiKey(apiKey);
      encrypted = encryptionResult.encrypted;
      version = encryptionResult.version;
    }

    // 11.5. Check if provider changed and load default model if needed
    const currentProvider = tomoriState.llm.llm_provider.toLowerCase();
    const newProvider = normalizedProvider;
    let newLlmId = tomoriState.config.llm_id; // Default to current model
    let newDiffusionModelId = tomoriState.config.diffusion_model_id; // Default to current diffusion model
    let newEmbeddingModelId = tomoriState.config.embedding_model_id; // Default to current embedding model

    if (currentProvider !== newProvider) {
      // Note: rotation keys are NOT purged on provider change — they are already
      // scoped by the `provider` column and filtered at runtime in selectApiKey().
      // They naturally persist and resume working when the user switches back.

      // Provider changed - handle custom provider specially
      if (isCustomProvider(newProvider)) {
        // Custom provider: use the LLM ID from capabilities configuration
        if (customCapabilitiesResult?.llmId) {
          newLlmId = customCapabilitiesResult.llmId;
          log.info(`Using custom LLM ID: ${newLlmId}`);
        } else {
          log.error(`Custom provider selected but no LLM ID available`);
          await replyInfoEmbed(modalSubmitInteraction, locale, {
            titleKey: "general.errors.operation_failed_title",
            descriptionKey: "commands.config.custom.capabilities_timeout",
            color: ColorCode.ERROR,
          });
          return;
        }

        // Custom provider doesn't have diffusion models
        newDiffusionModelId = null;
        // Custom provider doesn't have embedding models
        newEmbeddingModelId = null;
      } else {
        // Regular provider: load default model for new provider
        log.info(
          `Provider changed from ${currentProvider} to ${newProvider}, loading default model`,
        );
        const defaultModel = await loadDefaultModelForProvider(newProvider);

        if (!defaultModel || !defaultModel.llm_id) {
          await replyInfoEmbed(modalSubmitInteraction, locale, {
            titleKey: "commands.config.apikey.set.no_default_model_title",
            descriptionKey:
              "commands.config.apikey.set.no_default_model_description",
            descriptionVars: {
              provider: getProviderDisplayName(newProvider),
            },
            color: ColorCode.ERROR,
          });
          return;
        }

        newLlmId = defaultModel.llm_id;
        log.info(
          `Switching to default model for ${newProvider}: ${defaultModel.llm_codename} (ID: ${newLlmId})`,
        );

        // Load default diffusion model for new provider (for image generation)
        const defaultDiffusionModel = (
          await sql`
						SELECT * FROM image_diffusion_models
						WHERE provider = ${newProvider}
						  AND is_default = true
						  AND is_deprecated = false
						ORDER BY diffusion_model_id ASC
						LIMIT 1
					`
        )[0];

        // Fallback: if no default diffusion model found, get the first available non-deprecated model
        if (!defaultDiffusionModel) {
          const fallbackDiffusionModel = (
            await sql`
							SELECT * FROM image_diffusion_models
							WHERE provider = ${newProvider}
							  AND is_deprecated = false
							ORDER BY diffusion_model_id ASC
							LIMIT 1
						`
          )[0];

          if (fallbackDiffusionModel) {
            newDiffusionModelId = fallbackDiffusionModel.diffusion_model_id;
            log.warn(
              `No default diffusion model found for ${newProvider}, using fallback: ${fallbackDiffusionModel.codename}`,
            );
          } else {
            newDiffusionModelId = null;
            log.info(
              `No diffusion models available for ${newProvider} (image generation not supported)`,
            );
          }
        } else {
          newDiffusionModelId = defaultDiffusionModel.diffusion_model_id;
          log.info(
            `Switching to default diffusion model for ${newProvider}: ${defaultDiffusionModel.codename} (ID: ${newDiffusionModelId})`,
          );
        }

        // Load default embedding model for new provider (for document retrieval)
        const defaultEmbeddingModel = (
          await sql`
						SELECT * FROM embedding_models
						WHERE provider = ${newProvider}
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
							WHERE provider = ${newProvider}
							  AND is_deprecated = false
							ORDER BY embedding_model_id ASC
							LIMIT 1
						`
          )[0];

          if (fallbackEmbeddingModel) {
            newEmbeddingModelId = fallbackEmbeddingModel.embedding_model_id;
            log.warn(
              `No default embedding model found for ${newProvider}, using fallback: ${fallbackEmbeddingModel.codename}`,
            );
          } else {
            newEmbeddingModelId = null;
            log.info(
              `No embedding models available for ${newProvider} (document retrieval not supported)`,
            );
          }
        } else {
          newEmbeddingModelId = defaultEmbeddingModel.embedding_model_id;
          log.info(
            `Switching to default embedding model for ${newProvider}: ${defaultEmbeddingModel.codename} (ID: ${newEmbeddingModelId})`,
          );
        }
      }
    }

    // 12. Update the config in the database (includes llm_id, diffusion_model_id, embedding_model_id, custom_endpoint_url, and custom_model_name if provider changed)
    const customModelName = customCapabilitiesResult?.modelName || null;
    const targetLlm =
      newLlmId === tomoriState.config.llm_id
        ? tomoriState.llm
        : await loadLlmById(newLlmId);
    const resolvedLogitBiases = resolveLogitBiasEntriesForLlm(
      tomoriState.config.llm_logit_biases ?? [],
      targetLlm,
    );
    const resolvedLogitBiasesJson = JSON.stringify(resolvedLogitBiases.entries);
    const [updatedRow] = await sql`
			UPDATE tomori_configs
			SET api_key = ${encrypted},
			    key_version = ${version},
			    llm_id = ${newLlmId},
			    diffusion_model_id = ${newDiffusionModelId},
			    embedding_model_id = ${newEmbeddingModelId},
			    llm_logit_biases = ${resolvedLogitBiasesJson}::jsonb,
			    custom_endpoint_url = ${customEndpointUrl},
			    custom_model_name = ${customModelName}
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
          command: "config apikeyset",
          selectedProvider,
          validationErrors: validatedConfig.success
            ? null
            : validatedConfig.error.flatten(),
        },
      };
      await log.error(
        "Failed to update or validate config after setting API key",
        validatedConfig.success
          ? new Error("Database update returned no rows or unexpected data")
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

    // 14. Invalidate cache so next message gets fresh config
    invalidateTomoriStateCache(serverId);

    // 14.1. On provider change, clear scoped model overrides that reference
    // models from the old provider — both channel and persona overrides.
    // Non-critical: log failures but do not abort the key-set flow.
    if (currentProvider !== newProvider) {
      invalidateAllChannelLlmCacheForServer(tomoriState.server_id);
      const channelCleared = await clearAllChannelLlmOverridesForServer(
        tomoriState.server_id,
      );
      const personaCleared = await clearAllPersonaLlmOverridesForServer(
        tomoriState.server_id,
      );
      log.info(
        `Provider change ${currentProvider}→${newProvider}: ` +
          `channel overrides cleared=${channelCleared}, persona overrides cleared=${personaCleared}`,
      );
    }

    // 14.3. NovelAI auto-disable: when switching TO NovelAI, flip emoji and sticker
    // usage off. Both default to true on every config row, but NovelAI's token budget
    // makes them counterproductive. The user is notified in the success embed and can
    // re-enable via /config permissions. Only fires on provider switch, not key updates.
    if (currentProvider !== newProvider && newProvider === "novelai") {
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
        // Non-critical — log but don't fail the key update
        log.warn(
          `Failed to auto-disable emoji/sticker for NovelAI switch: ${disableError}`,
        );
      }
    }

    // 14.5. Success message (include model info if provider changed)
    // When switching specifically to NovelAI, use the dedicated key that also
    // notifies the user that emoji/sticker usage were automatically disabled.
    const successDescriptionKey =
      isCustomProvider(newProvider)
        ? "commands.config.apikey.set.custom_success_with_model_description"
        : currentProvider !== newProvider && newProvider === "novelai"
        ? "commands.config.apikey.set.novelai_success_with_model_description"
        : currentProvider !== newProvider
          ? "commands.config.apikey.set.success_with_model_description"
          : "commands.config.apikey.set.success_description";

    const descriptionVars: Record<string, string> = {
      provider: getProviderDisplayName(selectedProvider),
    };

    // Custom endpoint success copy always references {model_name}, even when the
    // provider stays on "custom" and the user is only reconfiguring the endpoint.
    if (isCustomProvider(newProvider)) {
      descriptionVars.model_name =
        customCapabilitiesResult?.modelName ||
        localizer(locale, "general.unknown");
    } else if (currentProvider !== newProvider) {
      const defaultModel = await loadDefaultModelForProvider(newProvider);
      if (defaultModel) {
        descriptionVars.model_name = defaultModel.llm_codename;
      }
    }

    await replyInfoEmbed(modalSubmitInteraction, locale, {
      titleKey: "commands.config.apikey.set.success_title",
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
        command: "config apikeyset",
        guildId: interaction.guild?.id,
        executorDiscordId: interaction.user.id,
      },
    };
    await log.error(
      `Error executing /config apikeyset for user ${userData.user_disc_id}`,
      error as Error,
      context,
    );

    // Inform user of unknown error
    // Use modalSubmitInteraction if available (error after modal), otherwise interaction (error during modal)
    const replyTarget = modalSubmitInteraction ?? interaction;
    await replyInfoEmbed(replyTarget, locale, {
      titleKey: "general.errors.unknown_error_title",
      descriptionKey: "general.errors.unknown_error_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
  }
}
