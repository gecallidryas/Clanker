import { OpenAICompatibleStreamAdapter } from "@/providers/openaiCompatible/openaiCompatibleStreamAdapter";
import type { OpenAICompatibleStreamConfig } from "@/providers/openaiCompatible/openaiCompatibleTypes";
import { ZAI_REASONING_MODELS } from "@/providers/zai/zaiShared";

export interface ZaicodingStreamConfig extends OpenAICompatibleStreamConfig {
	endpointUrl: string;
}

/**
 * Stream adapter for the Z.ai Coding API.
 * Handles reasoning content preservation, tool_stream flag, and output prefill.
 */
export class ZaicodingStreamAdapter extends OpenAICompatibleStreamAdapter {
	constructor() {
		super({
			providerName: "zaicoding",
			adapterName: "ZaicodingStreamAdapter",
			localeNamespace: ["genai", "zai"].join("."),
			errorMessagePrefix: "Z.ai API error",
			preserveReasoningContent: true,
			resolveApiUrl: (config) => {
				if (!config.endpointUrl) {
					throw new Error("Z.ai endpoint URL is required");
				}
				return config.endpointUrl;
			},
			mutateRequestBody: ({ requestBody, config, context }) => {
				const isReasoningModel = ZAI_REASONING_MODELS.includes(config.model);
				const thinkingEnabled = isReasoningModel || config.forceReason === true;
				if (thinkingEnabled) {
					requestBody.thinking = { type: "enabled", budget_tokens: 8192 };
					delete requestBody.temperature;
					delete requestBody.top_p;
					delete requestBody.presence_penalty;
					delete requestBody.frequency_penalty;
				}

				if (
					Array.isArray(requestBody.tools) &&
					requestBody.tools.length > 0
				) {
					requestBody.tool_stream = true;
				}

				const outputPrefill = context.outputPrefill?.trim();
				if (!outputPrefill) {
					return;
				}

				const messages = requestBody.messages;
				if (!Array.isArray(messages) || messages.length === 0) {
					return;
				}

				const lastMessage = messages.at(-1);
				if (
					!lastMessage ||
					typeof lastMessage !== "object" ||
					lastMessage.role !== "assistant" ||
					lastMessage.content !== outputPrefill
				) {
					return;
				}

				lastMessage.prefix = true;
			},
		});
	}
}
