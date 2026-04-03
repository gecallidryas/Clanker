import type {
  EmbeddingRequest,
} from "@/types/provider/featureInterfaces";
import { log } from "@/utils/misc/logger";
import { resolveEmbeddingsCapability } from "@/utils/provider/providerCapabilityResolver";

export type EmbeddingProviderName = string;
export type { EmbeddingTaskType, EmbeddingRequest } from "@/types/provider/featureInterfaces";

export async function providerSupportsEmbeddingTaskType(
  providerName: string,
): Promise<boolean> {
  const capability = await resolveEmbeddingsCapability(providerName);
  return capability?.supportsEmbeddingTaskType() ?? false;
}

async function generateEmbeddingsOnce(
  request: EmbeddingRequest,
): Promise<number[][]> {
  if (request.inputs.length === 0) {
    return [];
  }

  const capability = await resolveEmbeddingsCapability(request.provider);
  if (!capability) {
    throw new Error(`Unsupported embedding provider: ${request.provider}`);
  }

  return await capability.generateEmbeddings(request);
}

export async function generateEmbeddings(
  request: EmbeddingRequest,
): Promise<number[][]> {
  try {
    const embeddings = await generateEmbeddingsOnce(request);
    if (embeddings.length !== request.inputs.length) {
      throw new Error(
        `Embedding count mismatch: expected ${request.inputs.length}, got ${embeddings.length}`,
      );
    }
    return embeddings;
  } catch (error) {
    log.error(
      `Failed to generate embeddings for provider ${request.provider} model ${request.model}`,
      error,
    );
    throw error;
  }
}

export async function generateEmbeddingsBatched(
  request: EmbeddingRequest & { batchSize?: number },
): Promise<number[][]> {
  const { batchSize = 16, inputs } = request;
  if (inputs.length === 0) {
    return [];
  }

  const results: number[][] = [];
  for (let i = 0; i < inputs.length; i += batchSize) {
    const batch = inputs.slice(i, i + batchSize);
    const batchEmbeddings = await generateEmbeddings({
      ...request,
      inputs: batch,
    });
    results.push(...batchEmbeddings);
  }

  return results;
}
