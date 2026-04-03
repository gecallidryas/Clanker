/**
 * Provider stop-string helpers.
 *
 * These utilities keep turn-boundary stop behavior consistent across providers
 * while preserving first-turn behavior (a response can still begin with "Name:").
 */

/**
 * Build a newline-prefixed speaker stop string for the current persona.
 * Example: "\nTomori:"
 *
 * Newline prefix is intentional so an initial "Tomori:" at the very beginning
 * of a response is not blocked.
 */
export function buildPersonaSpeakerStopString(
  personaName?: string | null,
): string | null {
  if (!personaName) return null;

  const normalizedName = personaName
    .replace(/[\r\n]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!normalizedName) return null;

  return `\n${normalizedName}:`;
}

/**
 * Merge one stop string into an existing stop list, preserving order and
 * avoiding duplicates.
 */
export function mergeStopStrings(
  existingStops: string[] | undefined,
  additionalStop: string | null,
): string[] | undefined {
  const sanitizedExisting = (existingStops ?? []).filter(
    (stop): stop is string => typeof stop === "string" && stop.length > 0,
  );

  if (!additionalStop) {
    return sanitizedExisting.length > 0 ? sanitizedExisting : undefined;
  }

  if (sanitizedExisting.includes(additionalStop)) {
    return sanitizedExisting;
  }

  return [...sanitizedExisting, additionalStop];
}
