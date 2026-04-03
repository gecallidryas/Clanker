import { OpenAICompatibleStreamAdapter } from "@/providers/openaiCompatible/openaiCompatibleStreamAdapter";
import type { OpenAICompatibleStreamConfig } from "@/providers/openaiCompatible/openaiCompatibleTypes";

export interface DeepseekStreamConfig extends OpenAICompatibleStreamConfig {
	endpointUrl: string;
}

const DEEPSEEK_REASONER_MODEL = "deepseek-reasoner";
const DEEPSEEK_CHAT_MODEL = "deepseek-chat";

export class DeepseekStreamAdapter extends OpenAICompatibleStreamAdapter {
	constructor() {
		super({
			providerName: "deepseek",
			adapterName: "DeepseekStreamAdapter",
			localeNamespace: ["genai", "deepseek"].join("."),
			errorMessagePrefix: "DeepSeek API error",
			preserveReasoningContent: true,
			resolveApiUrl: (config) => {
				if (!config.endpointUrl) {
					throw new Error("DeepSeek endpoint URL is required");
				}
				return config.endpointUrl;
			},
			mutateRequestBody: ({ requestBody, config, context }) => {
				const thinkingEnabled =
					config.model === DEEPSEEK_REASONER_MODEL || config.forceReason === true;
				if (thinkingEnabled) {
					if (config.model === DEEPSEEK_CHAT_MODEL) {
						requestBody.thinking = { type: "enabled" };
					}
					delete requestBody.temperature;
					delete requestBody.top_p;
					delete requestBody.presence_penalty;
					delete requestBody.frequency_penalty;
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
