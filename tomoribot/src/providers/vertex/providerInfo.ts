/**
 * Vertex AI provider metadata and capability flags
 *
 * Feature parity with Google AI Studio — all helpers accept an optional
 * pre-built GoogleGenAI client, so Vertex passes its ADC client through.
 *
 * Exceptions (not yet implemented):
 *   - nativeImageGeneration: requires generateNativeImage() — not in VertexProvider
 *   - liveTokenCounting: requires measureInputTokens() — not in VertexProvider
 */

import type { ProviderInfo } from "../../types/provider/interfaces";

export const vertexProviderInfo: ProviderInfo = {
	name: "vertex",
	displayName: "Google Vertex AI",
	aliases: ["vertexai"],
	supportedModels: [],
	requiresApiKey: true,
	supportsStreaming: true,
	supportsFunctionCalling: true,
	supportsImages: true,
	supportsVideos: true,
	apiFamily: "google-genai",
	featureSupport: {
		nativeImageGeneration: false,
		embeddings: true,
		structuredOutput: true,
		presetGeneration: true,
		expressionInitialization: true,
		liveTokenCounting: false,
		conversationCompaction: true,
		historyExtraction: true,
	},
};
