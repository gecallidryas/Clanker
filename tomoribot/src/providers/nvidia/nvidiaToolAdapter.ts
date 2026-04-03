import { OpenAICompatibleToolAdapter } from "@/providers/openaiCompatible/openaiCompatibleToolAdapter";

export class NvidiaToolAdapter extends OpenAICompatibleToolAdapter {
	private static instance: NvidiaToolAdapter;

	private constructor() {
		super("nvidia");
	}

	static getInstance(): NvidiaToolAdapter {
		if (!NvidiaToolAdapter.instance) {
			NvidiaToolAdapter.instance = new NvidiaToolAdapter();
		}
		return NvidiaToolAdapter.instance;
	}
}

export function getNvidiaToolAdapter(): NvidiaToolAdapter {
	return NvidiaToolAdapter.getInstance();
}
