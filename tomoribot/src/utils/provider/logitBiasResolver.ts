import { encode as encodeCl100kBase } from "gpt-tokenizer/encoding/cl100k_base";
import { encode as encodeO200kBase } from "gpt-tokenizer/encoding/o200k_base";
import { encode as encodeO200kHarmony } from "gpt-tokenizer/encoding/o200k_harmony";
import { encode as encodeP50kBase } from "gpt-tokenizer/encoding/p50k_base";
import { encode as encodeP50kEdit } from "gpt-tokenizer/encoding/p50k_edit";
import { encode as encodeR50kBase } from "gpt-tokenizer/encoding/r50k_base";
import type { LlmRow } from "@/types/db/schema";
import {
	getLocalLogitBiasTokenizerEncoder,
	isLocalLogitBiasTokenizerFamily,
	resolveLocalLogitBiasTokenizerFamily,
} from "@/utils/provider/localTokenizerRegistry";
import {
	buildRuntimeLogitBiasMap,
	countRuntimeReadyLogitBiasEntries,
	type LogitBiasEntry,
	upsertLogitBiasTokenization,
} from "@/types/provider/logitBias";
import { getOpenRouterTokenizer } from "@/utils/cache/openrouterCapabilityCache";
import { log } from "@/utils/misc/logger";

type OpenAiBpeEncoding =
	| "cl100k_base"
	| "o200k_base"
	| "o200k_harmony"
	| "p50k_base"
	| "p50k_edit"
	| "r50k_base";

type OpenAiEncodingFn = (text: string) => number[];
type LogitBiasTextEncoder = (text: string) => number[];

const OPENAI_BPE_ENCODERS: Record<OpenAiBpeEncoding, OpenAiEncodingFn> = {
	cl100k_base: encodeCl100kBase,
	o200k_base: encodeO200kBase,
	o200k_harmony: encodeO200kHarmony,
	p50k_base: encodeP50kBase,
	p50k_edit: encodeP50kEdit,
	r50k_base: encodeR50kBase,
};

export interface LogitBiasResolutionResult {
	entries: LogitBiasEntry[];
	tokenizerKey: string | null;
	resolvedEntryCount: number;
	runtimeReadyCount: number;
}

export function resolveLogitBiasEntriesForLlm(
	entries: LogitBiasEntry[],
	llm: LlmRow | null | undefined,
): LogitBiasResolutionResult {
	const tokenizerKey = getLogitBiasTokenizerKeyForLlm(llm);
	if (!tokenizerKey) {
		return {
			entries,
			tokenizerKey: null,
			resolvedEntryCount: 0,
			runtimeReadyCount: countRuntimeReadyLogitBiasEntries(entries),
		};
	}

	const encoder = getLogitBiasTextEncoderForKey(tokenizerKey);
	if (!encoder) {
		return {
			entries,
			tokenizerKey,
			resolvedEntryCount: 0,
			runtimeReadyCount: countRuntimeReadyLogitBiasEntries(entries, tokenizerKey),
		};
	}

	let resolvedEntryCount = 0;
	const resolvedEntries = entries.map((entry) => {
		if (entry.kind === "token_id") {
			return entry;
		}

		const tokenIds = new Set<string>();
		for (const variant of buildLogitBiasTextVariants(entry.text)) {
			try {
				for (const tokenId of encoder(variant)) {
					tokenIds.add(tokenId.toString());
				}
			} catch (error) {
				log.warn("Failed to tokenize logit bias term variant", {
					error: error as Error,
					llmProvider: llm?.llm_provider,
					llmCodename: llm?.llm_codename,
					tokenizerKey,
					variant,
				});
			}
		}

		if (tokenIds.size === 0) {
			return entry;
		}

		const updatedEntry = upsertLogitBiasTokenization(
			entry,
			tokenizerKey,
			Array.from(tokenIds),
		);

		if (JSON.stringify(updatedEntry) !== JSON.stringify(entry)) {
			resolvedEntryCount++;
		}

		return updatedEntry;
	});

	return {
		entries: resolvedEntries,
		tokenizerKey,
		resolvedEntryCount,
		runtimeReadyCount: countRuntimeReadyLogitBiasEntries(
			resolvedEntries,
			tokenizerKey,
		),
	};
}

export function buildRuntimeLogitBiasMapForLlm(
	entries: LogitBiasEntry[],
	llm: LlmRow | null | undefined,
): Record<string, number> {
	return buildRuntimeLogitBiasMap(entries, getLogitBiasTokenizerKeyForLlm(llm));
}

export function getLogitBiasTokenizerKeyForLlm(
	llm: LlmRow | null | undefined,
): string | null {
	if (!llm) return null;

	const modelCodename = llm.llm_codename;
	const openRouterTokenizer =
		llm.llm_provider === "openrouter"
			? getOpenRouterTokenizer(modelCodename)
			: undefined;

	return resolveLogitBiasTokenizerKey(openRouterTokenizer, modelCodename);
}

function resolveOpenAiBpeEncoding(
	rawTokenizer: string | null | undefined,
	modelCodename: string,
): OpenAiBpeEncoding | null {
	const normalizedTokenizer = rawTokenizer?.trim().toLowerCase() ?? "";
	const normalizedModelCodename = modelCodename.trim().toLowerCase();

	if (
		normalizedTokenizer.includes("o200k_harmony") ||
		normalizedTokenizer.includes("harmony")
	) {
		return "o200k_harmony";
	}

	if (normalizedTokenizer.includes("o200k")) {
		return "o200k_base";
	}

	if (normalizedTokenizer.includes("cl100k")) {
		return "cl100k_base";
	}

	if (normalizedTokenizer.includes("p50k_edit")) {
		return "p50k_edit";
	}

	if (normalizedTokenizer.includes("p50k")) {
		return "p50k_base";
	}

	if (normalizedTokenizer.includes("r50k")) {
		return "r50k_base";
	}

	if (normalizedModelCodename.includes("gpt-oss-")) {
		return "o200k_harmony";
	}

	if (
		normalizedModelCodename.includes("gpt-5") ||
		normalizedModelCodename.includes("gpt-4.1") ||
		normalizedModelCodename.includes("gpt-4o") ||
		/(^|\/)o1([-/]|$)/.test(normalizedModelCodename) ||
		/(^|\/)o3([-/]|$)/.test(normalizedModelCodename) ||
		/(^|\/)o4([-/]|$)/.test(normalizedModelCodename)
	) {
		return "o200k_base";
	}

	if (
		normalizedModelCodename.includes("gpt-4") ||
		normalizedModelCodename.includes("gpt-3.5")
	) {
		return "cl100k_base";
	}

	if (
		normalizedModelCodename.includes("text-davinci-003") ||
		normalizedModelCodename.includes("text-davinci-002") ||
		normalizedModelCodename.includes("davinci-002") ||
		normalizedModelCodename.includes("code-davinci-002") ||
		normalizedModelCodename.includes("code-cushman-002")
	) {
		return "p50k_base";
	}

	if (
		normalizedModelCodename.includes("text-davinci-001") ||
		normalizedModelCodename === "davinci" ||
		normalizedModelCodename === "curie" ||
		normalizedModelCodename === "babbage" ||
		normalizedModelCodename === "ada"
	) {
		return "r50k_base";
	}

	return null;
}

function resolveLogitBiasTokenizerKey(
	rawTokenizer: string | null | undefined,
	modelCodename: string,
): string | null {
	return (
		resolveOpenAiBpeEncoding(rawTokenizer, modelCodename) ??
		resolveLocalLogitBiasTokenizerFamily(rawTokenizer, modelCodename)
	);
}

function getLogitBiasTextEncoderForKey(
	tokenizerKey: string,
): LogitBiasTextEncoder | null {
	const openAiEncoder = OPENAI_BPE_ENCODERS[tokenizerKey as OpenAiBpeEncoding];
	if (openAiEncoder) {
		return openAiEncoder;
	}

	if (isLocalLogitBiasTokenizerFamily(tokenizerKey)) {
		return getLocalLogitBiasTokenizerEncoder(tokenizerKey);
	}

	return null;
}

function buildLogitBiasTextVariants(text: string): string[] {
	const trimmed = text.trim();
	const variants = new Set<string>();

	if (trimmed.length === 0) {
		return [];
	}

	variants.add(trimmed);
	variants.add(` ${trimmed}`);

	const capitalized = `${trimmed.charAt(0).toUpperCase()}${trimmed.slice(1)}`;
	if (capitalized !== trimmed) {
		variants.add(capitalized);
		variants.add(` ${capitalized}`);
	}

	return Array.from(variants);
}
