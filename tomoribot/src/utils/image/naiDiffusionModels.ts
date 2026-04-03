import type { TomoriConfigRow } from "@/types/db/schema";
import { sql } from "@/utils/db/client";
import { log } from "@/utils/misc/logger";

export type NaiDiffusionModelSource = "override" | "shared" | "default";

export type ResolvedNaiDiffusionModel = {
	diffusionModelId: number;
	codename: string;
	source: NaiDiffusionModelSource;
};

type NaiDiffusionModelConfig = Pick<
	TomoriConfigRow,
	"diffusion_model_id" | "nai_diffusion_model_id"
>;

export type DiffusionModelFields = {
	diffusion_model_id: number;
	provider: string;
	codename: string;
	model_description: string | null;
	ja_description: string | null;
	is_default: boolean;
	is_deprecated: boolean;
	is_free: boolean;
	is_uncensored: boolean;
};

export async function getDiffusionModelById(
	diffusionModelId: number,
): Promise<DiffusionModelFields | null> {
	const [model] = await sql<DiffusionModelFields[]>`
		SELECT
			diffusion_model_id,
			provider,
			codename,
			model_description,
			ja_description,
			is_default,
			is_deprecated,
			is_free,
			is_uncensored
		FROM image_diffusion_models
		WHERE diffusion_model_id = ${diffusionModelId}
		LIMIT 1
	`;

	return model ?? null;
}

export async function getNovelAiDiffusionModels(): Promise<
	DiffusionModelFields[]
> {
	return sql<DiffusionModelFields[]>`
		SELECT
			diffusion_model_id,
			provider,
			codename,
			model_description,
			ja_description,
			is_default,
			is_deprecated,
			is_free,
			is_uncensored
		FROM image_diffusion_models
		WHERE provider = 'novelai'
			AND is_deprecated = false
		ORDER BY is_default DESC, codename
	`;
}

export async function getDefaultNovelAiDiffusionModel(): Promise<
	DiffusionModelFields
> {
	const [defaultModel] = await sql<DiffusionModelFields[]>`
		SELECT
			diffusion_model_id,
			provider,
			codename,
			model_description,
			ja_description,
			is_default,
			is_deprecated,
			is_free,
			is_uncensored
		FROM image_diffusion_models
		WHERE provider = 'novelai'
			AND is_default = true
			AND is_deprecated = false
		LIMIT 1
	`;

	if (!defaultModel) {
		throw new Error(
			"No default NovelAI diffusion model found in database. Please seed the database.",
		);
	}

	return defaultModel;
}

export function getLocalizedDiffusionModelDescription(
	model: DiffusionModelFields,
	locale: string,
): string {
	const normalizedLocale = locale.toLowerCase().split("-")[0];
	const description =
		normalizedLocale === "ja" ? model.ja_description : model.model_description;

	const baseDescription =
		description ?? model.model_description ?? `${model.provider} model`;

	const flags: string[] = [];
	if (model.is_free) flags.push("FREE");
	if (model.is_uncensored) flags.push("UNCENSORED");

	const flagPrefix = flags.length > 0 ? `(${flags.join("+")}) ` : "";
	return `${flagPrefix}${baseDescription}`;
}

export async function resolveNaiDiffusionModel(
	config: NaiDiffusionModelConfig,
): Promise<ResolvedNaiDiffusionModel> {
	if (config.nai_diffusion_model_id != null) {
		const overrideModel = await getDiffusionModelById(
			config.nai_diffusion_model_id,
		);
		if (overrideModel?.provider === "novelai") {
			return {
				diffusionModelId: overrideModel.diffusion_model_id,
				codename: overrideModel.codename,
				source: "override",
			};
		}

		log.warn(
			overrideModel
				? `[NAI] Configured nai_diffusion_model_id "${overrideModel.codename}" (provider: ${overrideModel.provider}) is not a NovelAI model. Ignoring dedicated override.`
				: `[NAI] Configured nai_diffusion_model_id ${config.nai_diffusion_model_id} was not found. Ignoring dedicated override.`,
		);
	}

	if (config.diffusion_model_id != null) {
		const sharedModel = await getDiffusionModelById(config.diffusion_model_id);
		if (sharedModel?.provider === "novelai") {
			return {
				diffusionModelId: sharedModel.diffusion_model_id,
				codename: sharedModel.codename,
				source: "shared",
			};
		}

		if (sharedModel) {
			log.warn(
				`[NAI] Shared diffusion model "${sharedModel.codename}" (provider: ${sharedModel.provider}) is not a NovelAI model. Falling back to default NovelAI model.`,
			);
		} else {
			log.warn(
				`[NAI] Shared diffusion_model_id ${config.diffusion_model_id} was not found. Falling back to default NovelAI model.`,
			);
		}
	}

	const defaultModel = await getDefaultNovelAiDiffusionModel();
	return {
		diffusionModelId: defaultModel.diffusion_model_id,
		codename: defaultModel.codename,
		source: "default",
	};
}
