import { OpenAICompatibleToolAdapter } from "@/providers/openaiCompatible/openaiCompatibleToolAdapter";

export class DeepseekToolAdapter extends OpenAICompatibleToolAdapter {
	private static instance: DeepseekToolAdapter;

	private constructor() {
		super("deepseek");
	}

	static getInstance(): DeepseekToolAdapter {
		if (!DeepseekToolAdapter.instance) {
			DeepseekToolAdapter.instance = new DeepseekToolAdapter();
		}
		return DeepseekToolAdapter.instance;
	}
}

export function getDeepseekToolAdapter(): DeepseekToolAdapter {
	return DeepseekToolAdapter.getInstance();
}
