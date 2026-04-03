import type { ProviderInfo } from "@/types/provider/interfaces";

export const nvidiaProviderInfo: ProviderInfo = {
	name: "nvidia",
	displayName: "NVIDIA NIM",
	aliases: ["nim"],
	supportedModels: [],
	requiresApiKey: true,
	supportsStreaming: true,
	supportsFunctionCalling: true,
	supportsImages: true,
	supportsVideos: false,
	apiFamily: "openai-compatible",
	featureSupport: {
		nativeImageGeneration: true,
		embeddings: true,
		structuredOutput: true,
		presetGeneration: true,
		expressionInitialization: false,
		liveTokenCounting: false,
		conversationCompaction: true,
		historyExtraction: true,
	},
};
