import type { LlmRow } from "@/types/db/schema";

export function getEffectiveLlmModelName(
	llm: LlmRow,
	customModelName?: string | null,
): string {
	const trimmedCustomModelName = customModelName?.trim();
	if (llm.llm_provider === "custom" && trimmedCustomModelName) {
		return trimmedCustomModelName;
	}

	return llm.llm_codename;
}

export function getLlmDisplayName(
	llm: LlmRow,
	customModelName?: string | null,
): string {
	return getEffectiveLlmModelName(llm, customModelName);
}

export function formatLlmDisplayLabel(
	llm: LlmRow,
	customModelName?: string | null,
): string {
	return `\`${getLlmDisplayName(llm, customModelName)}\` (${llm.llm_provider})`;
}
