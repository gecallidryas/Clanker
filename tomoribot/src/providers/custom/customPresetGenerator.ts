import { executeTool } from "@/tools/toolRegistry";
import type { ToolContext, ToolResult } from "@/types/tool/interfaces";
import type {
	GeneratePresetParams,
	PresetGenerationResult,
} from "@/types/provider/featureInterfaces";
import { log } from "@/utils/misc/logger";
import {
	sanitizeSampleDialogueText,
} from "@/providers/google/presetGenerator";
import { getCustomToolAdapter } from "@/providers/custom/customToolAdapter";
import {
	callCustomChatCompletions,
	extractCustomResponseText,
	parseCustomJsonResponse,
} from "@/providers/custom/customOpenAICompatibleUtils";
import {
	buildPresetResponseSchema,
	buildPresetPrompt,
	buildToolErrorResult,
	type PresetContentPart as CustomContentPart,
	type PresetMessage as CustomMessage,
	type PresetToolCall as CustomToolCall,
} from "@/providers/utils/presetCommon";

interface CustomPresetGenerationOptions {
	endpointUrl: string;
	model: string;
	temperature?: number;
	tools?: Array<Record<string, unknown>>;
	toolContext?: ToolContext;
	maxToolRounds?: number;
}

export async function generatePresetFromPromptCustom(
	apiKey: string,
	params: GeneratePresetParams,
	_optionsLocale: string,
	options: CustomPresetGenerationOptions,
): Promise<PresetGenerationResult> {
	const customAdapter = getCustomToolAdapter();
	const tools = options.tools ?? [];
	const toolContext = options.toolContext;
	const toolsEnabled = tools.length > 0 && toolContext;

	const responseFormat = {
		type: "json_schema" as const,
		json_schema: {
			name: "preset_export_data",
			description: "Structured persona preset data",
			schema: buildPresetResponseSchema(),
		},
	};

	const prompt = buildPresetPrompt(params);
	const contentParts: CustomContentPart[] = [{ type: "text", text: prompt }];

	if (params.imageBase64 && params.imageMimeType) {
		contentParts.push({
			type: "image_url",
			image_url: {
				url: `data:${params.imageMimeType};base64,${params.imageBase64}`,
			},
		});
		log.info("Custom preset generation: image included in prompt");
	}

	const userContent =
		contentParts.length === 1 && contentParts[0].type === "text"
			? contentParts[0].text
			: contentParts;

	const messages: CustomMessage[] = [
		{
			role: "user",
			content: userContent,
		},
	];

	const maxToolRounds = options.maxToolRounds ?? 3;
	let toolRounds = 0;

	while (true) {
		const body: Record<string, unknown> = {
			...(options.model !== "other-model" ? { model: options.model } : {}),
			messages,
			temperature: options.temperature ?? 1.0,
			max_tokens: 8192,
			response_format: responseFormat,
			stream: false,
		};

		if (toolsEnabled) {
			body.tools = tools;
			body.tool_choice = "auto";
		}

		const response = await callCustomChatCompletions({
			endpointUrl: options.endpointUrl,
			apiKey,
			body,
			logLabel: "Custom preset generation",
			messagesForLog: messages as Array<Record<string, unknown>>,
		});

		if (!response.success) {
			log.error(
				"Custom preset generation request failed",
				new Error(response.error.errorBody),
				{
					errorType: "CustomPresetGenerationHttpError",
					metadata: {
						model: options.model,
						status: response.error.status,
						errorBody: response.error.errorBody,
					},
				},
			);
			return {
				error:
					response.error.status === 0
						? response.error.errorBody
						: `Custom endpoint request failed (${response.error.status}): ${response.error.statusText}`,
				errorType: "CONNECTION",
			};
		}

		const message = response.data.choices?.[0]?.message as
			| {
					content?: unknown;
					tool_calls?: CustomToolCall[];
			  }
			| undefined;

		if (!message) {
			return {
				error: "Custom endpoint returned an empty response.",
				errorType: "EMPTY_RESPONSE",
			};
		}

		const toolCalls = message.tool_calls ?? [];
		if (toolCalls.length > 0) {
			if (!toolsEnabled || !toolContext) {
				return {
					error: "Custom endpoint requested tool calls but tools are not available.",
					errorType: "MODEL_ERROR",
				};
			}

			toolRounds += 1;
			if (toolRounds > maxToolRounds) {
				return {
					error: "Custom endpoint tool call loop exceeded limit.",
					errorType: "TIMEOUT",
				};
			}

			const normalizedToolCalls = toolCalls.map((toolCall, index) => ({
				...toolCall,
				id: toolCall.id ?? `tool_call_${toolRounds}_${index}`,
			}));

			messages.push({
				role: "assistant",
				content:
					typeof message.content === "string" ? message.content : null,
				tool_calls: normalizedToolCalls,
			});

			for (const toolCall of normalizedToolCalls) {
				const functionName = toolCall.function?.name;
				const rawArgs = toolCall.function?.arguments ?? "";

				let toolResult: ToolResult | undefined;
				let parsedArgs: Record<string, unknown> = {};

				if (!functionName) {
					toolResult = buildToolErrorResult(
						"Tool call missing function name",
					);
				} else {
					if (rawArgs) {
						try {
							parsedArgs = JSON.parse(rawArgs);
						} catch (parseError) {
							log.warn(
								`Custom tool call args parse failed for ${functionName}: ${rawArgs}`,
								parseError as Error,
							);
							toolResult = buildToolErrorResult(
								`Invalid tool arguments for ${functionName}`,
							);
						}
					}

					if (!toolResult) {
						log.info(
							`Executing custom preset-generation tool call: ${functionName} with args: ${JSON.stringify(parsedArgs)}`,
						);
						toolResult = await executeTool(
							functionName,
							parsedArgs,
							toolContext,
						);
					}
				}

				const convertedResult = customAdapter.convertResult(
					toolResult ?? buildToolErrorResult("Tool execution failed"),
				);
				const resultContent =
					typeof convertedResult.content === "string"
						? convertedResult.content
						: JSON.stringify(convertedResult.content);
				const toolCallId = toolCall.id ?? "tool_call_unknown";

				messages.push({
					role: "tool",
					tool_call_id: toolCallId,
					content: resultContent,
				});
			}

			continue;
		}

		const responseText = extractCustomResponseText(message.content);
		if (!responseText) {
			return {
				error: "Custom endpoint returned an empty response.",
				errorType: "EMPTY_RESPONSE",
			};
		}

		let parsedResponse: {
			attribute_list?: string[];
			sample_dialogues_in?: string[];
			sample_dialogues_out?: string[];
		};

		try {
			parsedResponse = parseCustomJsonResponse(responseText) as {
				attribute_list?: string[];
				sample_dialogues_in?: string[];
				sample_dialogues_out?: string[];
			};
		} catch (parseError) {
			log.error(
				"Custom preset generation JSON parse failed",
				parseError as Error,
			);
			return {
				error: "Invalid JSON response from custom endpoint.",
				errorType: "INVALID_JSON",
			};
		}

		if (
			!parsedResponse.attribute_list ||
			!parsedResponse.sample_dialogues_in ||
			!parsedResponse.sample_dialogues_out
		) {
			return {
				error: "Generated character data is incomplete. Please try again.",
				errorType: "INVALID_JSON",
			};
		}

		if (
			!Array.isArray(parsedResponse.attribute_list) ||
			parsedResponse.attribute_list.length !== 6
		) {
			return {
				error:
					"Generated attribute list must contain exactly 6 items. Please try again.",
				errorType: "VALIDATION_ERROR",
			};
		}

		if (
			!Array.isArray(parsedResponse.sample_dialogues_in) ||
			parsedResponse.sample_dialogues_in.length !== 5
		) {
			return {
				error: "Generated sample dialogues must contain exactly 5 user inputs.",
				errorType: "VALIDATION_ERROR",
			};
		}

		if (
			!Array.isArray(parsedResponse.sample_dialogues_out) ||
			parsedResponse.sample_dialogues_out.length !== 5
		) {
			return {
				error:
					"Generated sample dialogues must contain exactly 5 character responses.",
				errorType: "VALIDATION_ERROR",
			};
		}

		const sanitizedDialoguesIn = parsedResponse.sample_dialogues_in.map(
			sanitizeSampleDialogueText,
		);
		const sanitizedDialoguesOut = parsedResponse.sample_dialogues_out.map(
			sanitizeSampleDialogueText,
		);

		const preset = {
			tomori_nickname: params.characterName,
			trigger_words: [params.characterName],
			attribute_list: parsedResponse.attribute_list,
			sample_dialogues_in: sanitizedDialoguesIn,
			sample_dialogues_out: sanitizedDialoguesOut,
		};

		log.success(
			`Custom preset generation successful for ${params.characterName}`,
		);
		return { preset };
	}
}
