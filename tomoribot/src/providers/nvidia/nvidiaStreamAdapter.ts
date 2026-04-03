import { OpenAICompatibleStreamAdapter } from "@/providers/openaiCompatible/openaiCompatibleStreamAdapter";
import type { OpenAICompatibleStreamConfig } from "@/providers/openaiCompatible/openaiCompatibleTypes";

export interface NvidiaStreamConfig extends OpenAICompatibleStreamConfig {
	endpointUrl: string;
}

export class NvidiaStreamAdapter extends OpenAICompatibleStreamAdapter {
	constructor() {
		super({
			providerName: "nvidia",
			adapterName: "NvidiaStreamAdapter",
			localeNamespace: ["genai", "nvidia"].join("."),
			errorMessagePrefix: "NVIDIA API error",
			resolveApiUrl: (config) => {
				if (!config.endpointUrl) {
					throw new Error("NVIDIA endpoint URL is required");
				}
				return config.endpointUrl;
			},
		});
	}
}
