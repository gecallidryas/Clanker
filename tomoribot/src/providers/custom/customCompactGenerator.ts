import {
	buildCustomMessages,
	callCustomChatCompletions,
	extractCustomResponseText,
} from "@/providers/custom/customOpenAICompatibleUtils";
import { callCustomStructuredJSON } from "@/providers/custom/customStructuredOutput";
import type {
	CompactConversationResult,
	CompactRoleplayResult,
	ProviderCompactSummaryRequest as CompactSummaryRequest,
} from "@/types/provider/featureInterfaces";
import { log } from "@/utils/misc/logger";
import {
	buildRoleplaySchema,
	CompactRoleplaySummarySchema,
} from "@/providers/utils/compactCommon";

export async function generateConversationSummaryCustom(
	request: CompactSummaryRequest,
): Promise<CompactConversationResult> {
	try {
		const messages = await buildCustomMessages({
			systemPrompt: request.systemPrompt,
			userPrompt: request.userPrompt,
			images: request.images,
		});

		const body: Record<string, unknown> = {
			...(request.model !== "other-model" ? { model: request.model } : {}),
			messages,
			temperature: request.temperature ?? 0.7,
			max_tokens: 4096,
			stream: false,
		};

		const response = await callCustomChatCompletions({
			endpointUrl: request.endpointUrl,
			apiKey: request.apiKey,
			body,
			logLabel: "Custom compact summary",
			messagesForLog: messages as Array<Record<string, unknown>>,
		});

		if (!response.success) {
			log.error(
				"Custom compact summary request failed",
				new Error(response.error.errorBody),
				{
					errorType: "CustomCompactSummaryHttpError",
					metadata: {
						model: request.model,
						status: response.error.status,
						statusText: response.error.statusText,
					},
				},
			);
			return {
				error:
					response.error.status === 0
						? response.error.errorBody
						: `Custom endpoint request failed (${response.error.status}): ${response.error.statusText}`,
			};
		}

		const responseText = extractCustomResponseText(
			response.data.choices?.[0]?.message?.content,
		);
		if (!responseText) {
			return {
				error: "Custom endpoint returned an empty response.",
			};
		}

		return {
			summary: responseText,
		};
	} catch (error) {
		log.error("Custom compact summary failed", error as Error);
		return {
			error:
				error instanceof Error
					? error.message
					: "Unknown custom endpoint error",
		};
	}
}

export async function generateRoleplaySummaryCustom(
	request: CompactSummaryRequest,
): Promise<CompactRoleplayResult> {
	const result = await callCustomStructuredJSON(
		{
			...request,
			systemPrompt: request.systemPrompt ?? "",
			schemaName: "roleplay_summary",
		},
		buildRoleplaySchema(),
		CompactRoleplaySummarySchema,
	);

	if (!result.success) {
		return {
			error: result.error,
		};
	}

	return {
		summary: result.data,
	};
}
