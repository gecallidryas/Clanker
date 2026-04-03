import { OpenAICompatibleToolAdapter } from "@/providers/openaiCompatible/openaiCompatibleToolAdapter";

export class CustomToolAdapter extends OpenAICompatibleToolAdapter {
	private static instance: CustomToolAdapter;

	private constructor() {
		super("custom");
	}

	static getInstance(): CustomToolAdapter {
		if (!CustomToolAdapter.instance) {
			CustomToolAdapter.instance = new CustomToolAdapter();
		}
		return CustomToolAdapter.instance;
	}
}

export function getCustomToolAdapter(): CustomToolAdapter {
	return CustomToolAdapter.getInstance();
}
