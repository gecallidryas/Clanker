import {
  UNPAIRED_SAMPLE_DIALOGUE_SENTINEL,
  type PresetExportData,
} from "../../types/preset/presetExport";
import type { SillyTavernCardMetadata } from "../image/pngMetadata";
import { ABSOLUTE_MAX_ATTRIBUTES, getMemoryLimits } from "./memoryLimits";

type JsonObject = Record<string, unknown>;

type DialoguePair = {
  input: string;
  output: string;
};

type DialogueTurn = {
  speaker: "user" | "char";
  content: string;
};

type ContentSection = {
  heading?: string;
  content: string;
};

export type SillyTavernConversionResult =
  | {
      success: true;
      data: PresetExportData;
    }
  | {
      success: false;
      error: string;
    };

const CONTINUATION_MARKER = " [truncated]";

function asObject(value: unknown): JsonObject | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as JsonObject;
}

function getStringField(obj: JsonObject | null, key: string): string | null {
  if (!obj) {
    return null;
  }

  const value = obj[key];
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function getStringArrayField(obj: JsonObject | null, key: string): string[] {
  if (!obj) {
    return [];
  }

  const value = obj[key];
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is string => typeof item === "string")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function sanitizeSillyTavernText(input: string): string {
  return input
    .replace(/\r\n/g, "\n")
    .replace(/<!--[\s\S]*?--!?>/g, "")
    .trim();
}

function capitalizeFirstLetter(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) {
    return "Imported Persona";
  }

  return `${trimmed.charAt(0).toUpperCase()}${trimmed.slice(1)}`;
}

function truncateToMaxLength(input: string, maxLength: number): string {
  const text = input.trim();
  if (text.length <= maxLength) {
    return text;
  }

  const maxBody = Math.max(maxLength - CONTINUATION_MARKER.length, 0);
  return `${text.slice(0, maxBody).trimEnd()}${CONTINUATION_MARKER}`;
}

function splitLongTextIntoChunks(input: string, maxLength: number): string[] {
  const text = input.trim();
  if (!text) {
    return [];
  }

  if (text.length <= maxLength) {
    return [text];
  }

  const chunks: string[] = [];
  const paragraphs = text.split(/\n{2,}/).map((paragraph) => paragraph.trim());
  let currentChunk = "";

  for (const paragraph of paragraphs) {
    if (!paragraph) {
      continue;
    }

    if (paragraph.length > maxLength) {
      if (currentChunk) {
        chunks.push(currentChunk);
        currentChunk = "";
      }

      let offset = 0;
      while (offset < paragraph.length) {
        const rawChunk = paragraph.slice(offset, offset + maxLength);
        const chunk = rawChunk.trim();
        if (chunk) {
          chunks.push(chunk);
        }
        offset += maxLength;
      }
      continue;
    }

    if (!currentChunk) {
      currentChunk = paragraph;
      continue;
    }

    if (currentChunk.length + 2 + paragraph.length <= maxLength) {
      currentChunk = `${currentChunk}\n\n${paragraph}`;
    } else {
      chunks.push(currentChunk);
      currentChunk = paragraph;
    }
  }

  if (currentChunk) {
    chunks.push(currentChunk);
  }

  return chunks;
}

function buildAttributeSectionChunks(
  heading: string | undefined,
  content: string,
  maxAttributeLength: number,
): string[] {
  const sanitized = sanitizeSillyTavernText(content);
  if (!sanitized) {
    return [];
  }

  const prefix = heading ? `${heading}\n` : "";
  const maxContentLength = Math.max(maxAttributeLength - prefix.length, 200);
  const contentChunks = splitLongTextIntoChunks(sanitized, maxContentLength);
  return contentChunks.map((chunk) =>
    truncateToMaxLength(`${prefix}${chunk}`, maxAttributeLength),
  );
}

function normalizeSpeaker(rawLabel: string): "user" | "char" | null {
  const normalized = rawLabel.toLowerCase().replace(/[{}\s]/g, "");
  if (normalized === "user" || normalized === "you") {
    return "user";
  }

  if (
    normalized === "char" ||
    normalized === "bot" ||
    normalized === "assistant" ||
    normalized === "character"
  ) {
    return "char";
  }

  return null;
}

function collapseConsecutiveTurns(turns: DialogueTurn[]): DialogueTurn[] {
  const collapsed: DialogueTurn[] = [];
  for (const turn of turns) {
    const previous = collapsed[collapsed.length - 1];
    if (previous && previous.speaker === turn.speaker) {
      previous.content = `${previous.content}\n\n${turn.content}`.trim();
    } else {
      collapsed.push({ ...turn });
    }
  }
  return collapsed;
}

function parseSpeakerTurns(segment: string): DialogueTurn[] {
  const speakerPattern =
    /(?:^|\n)\s*(\{\{\s*(?:user|char|bot)\s*\}\}|\{\s*(?:user|char|bot)\s*\}|user|you|char|bot|character|assistant)\s*:\s*/gim;

  const matches: Array<{
    speaker: "user" | "char";
    start: number;
    end: number;
  }> = [];
  let match: RegExpExecArray | null;

  // biome-ignore lint/suspicious/noAssignInExpressions: Regex iteration idiom
  while ((match = speakerPattern.exec(segment)) !== null) {
    const speaker = normalizeSpeaker(match[1]);
    if (!speaker) {
      continue;
    }

    matches.push({
      speaker,
      start: match.index ?? 0,
      end: speakerPattern.lastIndex,
    });
  }

  if (matches.length === 0) {
    return [];
  }

  const turns: DialogueTurn[] = [];
  for (let i = 0; i < matches.length; i++) {
    const current = matches[i];
    const next = matches[i + 1];
    const contentStart = current.end;
    const contentEnd = next ? next.start : segment.length;
    const rawContent = segment.slice(contentStart, contentEnd).trim();
    if (!rawContent) {
      continue;
    }

    turns.push({
      speaker: current.speaker,
      content: sanitizeSillyTavernText(rawContent),
    });
  }

  return collapseConsecutiveTurns(turns);
}

function buildPairsFromTurns(
  turns: DialogueTurn[],
  maxDialogueLength: number,
  syntheticInput: string,
): DialoguePair[] {
  const pairs: DialoguePair[] = [];
  let pendingUser: string | null = null;

  for (const turn of turns) {
    if (turn.speaker === "user") {
      pendingUser = truncateToMaxLength(turn.content, maxDialogueLength);
      continue;
    }

    const output = truncateToMaxLength(turn.content, maxDialogueLength);
    if (!output) {
      continue;
    }

    const input = pendingUser ?? syntheticInput;
    pairs.push({
      input: truncateToMaxLength(input, maxDialogueLength),
      output,
    });
    pendingUser = null;
  }

  return pairs;
}

function parseMesExamplePairs(
  mesExample: string | null,
  maxDialogueLength: number,
): DialoguePair[] {
  if (!mesExample) {
    return [];
  }

  const cleaned = sanitizeSillyTavernText(mesExample);
  if (!cleaned) {
    return [];
  }

  const segments = cleaned
    .split(/(?:^|\n)\s*<START>\s*(?:\n|$)/gi)
    .map((segment) => segment.trim())
    .filter((segment) => segment.length > 0);

  const blocks = segments.length > 0 ? segments : [cleaned];
  const pairs: DialoguePair[] = [];

  for (const block of blocks) {
    const turns = parseSpeakerTurns(block);
    if (turns.length === 0) {
      pairs.push({
        input: UNPAIRED_SAMPLE_DIALOGUE_SENTINEL,
        output: truncateToMaxLength(block, maxDialogueLength),
      });
      continue;
    }

    pairs.push(
      ...buildPairsFromTurns(
        turns,
        maxDialogueLength,
        UNPAIRED_SAMPLE_DIALOGUE_SENTINEL,
      ),
    );
  }

  return pairs;
}

function buildGreetingPairs(
  firstMessage: string | null,
  alternateGreetings: string[],
  maxDialogueLength: number,
): DialoguePair[] {
  const rawOutputs: string[] = [];
  if (firstMessage) {
    rawOutputs.push(firstMessage);
  }
  rawOutputs.push(...alternateGreetings);

  return rawOutputs
    .map((text) => sanitizeSillyTavernText(text))
    .filter((text) => text.length > 0)
    .map((text) => ({
      input: UNPAIRED_SAMPLE_DIALOGUE_SENTINEL,
      output: truncateToMaxLength(text, maxDialogueLength),
    }));
}

function generateDefaultTriggerWords(
  name: string,
  maxTriggerWords: number,
): string[] {
  const triggers: string[] = [];
  const seen = new Set<string>();

  const pushUnique = (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    triggers.push(normalized);
  };

  pushUnique(name);
  for (const part of name.split(/[\s_-]+/)) {
    const alphanumeric = part.replace(/[^a-zA-Z0-9]/g, "").trim();
    if (alphanumeric.length >= 2) {
      pushUnique(alphanumeric);
    }
  }

  return triggers.slice(0, maxTriggerWords);
}

function pickStringFromCard(
  cardData: JsonObject | null,
  rootData: JsonObject,
  key: string,
): string | null {
  return getStringField(cardData, key) ?? getStringField(rootData, key);
}

function pickStringArrayFromCard(
  cardData: JsonObject | null,
  rootData: JsonObject,
  key: string,
): string[] {
  const fromData = getStringArrayField(cardData, key);
  if (fromData.length > 0) {
    return fromData;
  }

  return getStringArrayField(rootData, key);
}

function pickObjectFromCard(
  cardData: JsonObject | null,
  rootData: JsonObject,
  key: string,
): JsonObject | null {
  return asObject(cardData?.[key]) ?? asObject(rootData[key]);
}

function collectCharacterBookSections(
  characterBook: JsonObject | null,
): ContentSection[] {
  if (!characterBook) {
    return [];
  }

  const entriesRaw = characterBook.entries;
  if (!Array.isArray(entriesRaw)) {
    return [];
  }

  const sections: ContentSection[] = [];
  for (const entryRaw of entriesRaw) {
    const entry = asObject(entryRaw);
    if (!entry) {
      continue;
    }

    const isEnabled = entry.enabled !== false;
    if (!isEnabled) {
      continue;
    }

    const content = getStringField(entry, "content");
    if (!content) {
      continue;
    }

    let entryTitle = getStringField(entry, "name") ?? "";
    if (!entryTitle) {
      const keys = getStringArrayField(entry, "keys");
      if (keys.length > 0) {
        entryTitle = keys.slice(0, 3).join(", ");
      }
    }

    sections.push({
      heading: entryTitle
        ? `Character Book - ${entryTitle}`
        : "Character Book Entry",
      content,
    });
  }

  return sections;
}

export function convertSillyTavernMetadataToPresetData(
  metadata: SillyTavernCardMetadata,
): SillyTavernConversionResult {
  const rootData = asObject(metadata.parsedJson);
  if (!rootData) {
    return {
      success: false,
      error: "Decoded SillyTavern metadata is not a JSON object.",
    };
  }

  const cardData = asObject(rootData.data);
  const limits = getMemoryLimits();
  const maxAttributeLength = limits.maxAttributeLength;
  const maxDialogueLength = limits.maxSampleDialogueLength;
  const maxDialoguePairs = Math.max(limits.maxSampleDialogues, 1);
  const maxTriggerWords = Math.max(limits.maxTriggerWords, 1);

  const name =
    pickStringFromCard(cardData, rootData, "name") ??
    pickStringFromCard(cardData, rootData, "char_name") ??
    "Imported Persona";
  const normalizedName = capitalizeFirstLetter(name);

  const sections: ContentSection[] = [];

  const description = pickStringFromCard(cardData, rootData, "description");
  if (description) {
    sections.push({ content: description });
  }

  const personality = pickStringFromCard(cardData, rootData, "personality");
  if (personality) {
    sections.push({ heading: "Personality", content: personality });
  }

  const scenario = pickStringFromCard(cardData, rootData, "scenario");
  if (scenario) {
    sections.push({ heading: "Scenario", content: scenario });
  }

  const systemPrompt = pickStringFromCard(cardData, rootData, "system_prompt");
  if (systemPrompt) {
    sections.push({ heading: "System Prompt", content: systemPrompt });
  }

  const postHistoryInstructions = pickStringFromCard(
    cardData,
    rootData,
    "post_history_instructions",
  );
  if (postHistoryInstructions) {
    sections.push({
      heading: "Post-History Instructions",
      content: postHistoryInstructions,
    });
  }

  const extensions = pickObjectFromCard(cardData, rootData, "extensions");
  const depthPrompt = getStringField(
    asObject(extensions?.depth_prompt),
    "prompt",
  );
  if (depthPrompt) {
    sections.push({
      heading: "Depth Prompt",
      content: depthPrompt,
    });
  }

  const characterBook = pickObjectFromCard(
    cardData,
    rootData,
    "character_book",
  );
  sections.push(...collectCharacterBookSections(characterBook));

  const attributeList = sections
    .flatMap((section) =>
      buildAttributeSectionChunks(
        section.heading,
        section.content,
        maxAttributeLength,
      ),
    )
    .slice(0, ABSOLUTE_MAX_ATTRIBUTES);

  const mesExample = pickStringFromCard(cardData, rootData, "mes_example");
  const firstMessage = pickStringFromCard(cardData, rootData, "first_mes");
  const alternateGreetings = pickStringArrayFromCard(
    cardData,
    rootData,
    "alternate_greetings",
  );

  const dialoguePairs: DialoguePair[] = [];
  dialoguePairs.push(...parseMesExamplePairs(mesExample, maxDialogueLength));
  dialoguePairs.push(
    ...buildGreetingPairs(firstMessage, alternateGreetings, maxDialogueLength),
  );

  const cappedDialoguePairs = dialoguePairs.slice(0, maxDialoguePairs);

  const triggerWords = generateDefaultTriggerWords(
    normalizedName,
    maxTriggerWords,
  );

  return {
    success: true,
    data: {
      tomori_nickname: normalizedName,
      attribute_list: attributeList,
      sample_dialogues_in: cappedDialoguePairs.map((pair) => pair.input),
      sample_dialogues_out: cappedDialoguePairs.map((pair) => pair.output),
      trigger_words: triggerWords,
    },
  };
}
