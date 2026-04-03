import type { ProviderInfo } from "@/types/provider/interfaces";

export const novelaiProviderInfo: ProviderInfo = {
	name: "novelai",
	displayName: "NovelAI",
	aliases: ["nai"],
	supportedModels: [],
	requiresApiKey: true,
	supportsStreaming: true,
	supportsFunctionCalling: true,
	supportsImages: false,
	supportsVideos: false,
	apiFamily: "novelai",
	featureSupport: {
		nativeImageGeneration: false,
		embeddings: false,
		structuredOutput: false,
		presetGeneration: false,
		expressionInitialization: false,
		liveTokenCounting: false,
		conversationCompaction: false,
		historyExtraction: false,
	},
};
