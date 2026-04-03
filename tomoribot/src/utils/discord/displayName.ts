type DiscordUserIdentity = {
	displayName?: string | null;
	globalName?: string | null;
	username?: string | null;
};

function normalizeDisplayName(value?: string | null): string | null {
	const trimmed = value?.trim();
	return trimmed ? trimmed : null;
}

export function resolvePreferredDiscordDisplayName(params: {
	memberDisplayName?: string | null;
	user?: DiscordUserIdentity | null;
	fallback?: string | null;
}): string {
	return (
		normalizeDisplayName(params.memberDisplayName) ??
		normalizeDisplayName(params.user?.displayName) ??
		normalizeDisplayName(params.user?.globalName) ??
		normalizeDisplayName(params.user?.username) ??
		normalizeDisplayName(params.fallback) ??
		"User"
	);
}
