import {
	MessageFlags,
	type Attachment,
	type ChatInputCommandInteraction,
	type Client,
	type SlashCommandSubcommandBuilder,
} from "discord.js";
import { getCachedTomoriState } from "@/utils/cache/tomoriStateCache";
import { localizer } from "@/utils/text/localizer";
import { log, ColorCode } from "@/utils/misc/logger";
import { replyInfoEmbed } from "@/utils/discord/interactionHelper";
import { safeDownload } from "@/utils/security/safeDownload";
import { insertPresetWithNodes, setActivePreset } from "@/utils/db/stPresetDb";
import type { UserRow, ErrorContext, StPresetNodeRow } from "@/types/db/schema";

// ─── Constants ───────────────────────────────────────────────────────

/** Maximum file size for preset JSON uploads (in MB) */
const MAX_PRESET_FILE_SIZE_MB = 2;

/** Maximum allowed preset name length (derived from filename) */
const MAX_PRESET_NAME_LENGTH = 100;

/**
 * Regex to detect comment-only content in SillyTavern nodes.
 * Matches content that is purely `{{// ... }}` blocks and `{{trim}}` macros
 * with optional whitespace — meaning the node produces no output after
 * template resolution.
 */
const COMMENT_ONLY_REGEX = /^(\s*\{\{\/\/[^}]*\}\}\s*|\s*\{\{trim\}\}\s*)+$/;

// ─── Types ───────────────────────────────────────────────────────────

/** Raw prompt node from SillyTavern preset JSON */
interface RawSTPromptNode {
	identifier: string;
	name: string;
	role?: string;
	content?: string;
	system_prompt?: boolean;
	marker?: boolean;
	enabled?: boolean;
	injection_position?: number;
	injection_depth?: number;
	injection_order?: number;
	forbid_overrides?: boolean;
}

/** Entry in the prompt_order array */
interface RawSTPromptOrderEntry {
	identifier: string;
	enabled: boolean;
}

/** Top-level structure of a SillyTavern preset JSON */
interface RawSTPreset {
	prompts?: RawSTPromptNode[];
	prompt_order?: {
		character_id: number;
		order: RawSTPromptOrderEntry[];
	}[];
	[key: string]: unknown;
}

// ─── Subcommand Configuration ────────────────────────────────────────

/**
 * Configure the /stpreset upload subcommand.
 * Accepts a required JSON file attachment containing a SillyTavern preset.
 * @param subcommand - The subcommand builder
 */
export const configureSubcommand = (
	subcommand: SlashCommandSubcommandBuilder,
) =>
	subcommand
		.setName("upload")
		.setDescription(
			localizer("en-US", "commands.stpreset.upload.description"),
		)
		.addAttachmentOption((option) =>
			option
				.setName("file")
				.setDescription(
					localizer("en-US", "commands.stpreset.upload.file_description"),
				)
				.setRequired(true),
		);

// ─── Validation ──────────────────────────────────────────────────────

/**
 * Validate that the attachment is a JSON file.
 * @param attachment - Discord attachment to validate
 * @returns Validation result with optional error key
 */
function validateAttachment(attachment: Attachment): {
	isValid: boolean;
	errorKey?: string;
} {
	const filename = attachment.name?.toLowerCase() ?? "";

	// 1. Check file extension
	if (!filename.endsWith(".json")) {
		return { isValid: false, errorKey: "invalid_format" };
	}

	// 2. Check content type if provided (Discord may not always set this)
	if (attachment.contentType && !attachment.contentType.includes("json")) {
		return { isValid: false, errorKey: "invalid_format" };
	}

	return { isValid: true };
}

/**
 * Determine whether a prompt node is comment-only (produces no output).
 * Comment-only nodes contain only `{{// ... }}` blocks and `{{trim}}` macros.
 * @param content - The raw content string from the prompt node
 * @returns True if the content resolves to empty after macro processing
 */
function isCommentOnly(content: string): boolean {
	return COMMENT_ONLY_REGEX.test(content.trim());
}

/**
 * Derive a preset name from the uploaded filename.
 * Strips the .json extension and truncates to MAX_PRESET_NAME_LENGTH.
 * @param filename - Original filename from the Discord attachment
 * @returns Cleaned preset name
 */
function derivePresetName(filename: string): string {
	const name = filename.replace(/\.json$/i, "").trim();
	return name.length > MAX_PRESET_NAME_LENGTH
		? name.slice(0, MAX_PRESET_NAME_LENGTH)
		: name;
}

// ─── Preset Parsing ──────────────────────────────────────────────────

/** Result of parsing a preset, including nodes and filtering stats */
interface ParseResult {
	nodes: Omit<StPresetNodeRow, "node_id" | "preset_id">[];
	/** Number of comment-only nodes that were filtered out entirely */
	commentOnlySkipped: number;
	/** Number of non-marker nodes disabled by the preset's prompt_order */
	disabledByPreset: number;
}

/**
 * Parse a raw SillyTavern preset JSON into storable nodes.
 *
 * Processing pipeline:
 * 1. Build a lookup map from the `prompts` array (identifier → node data)
 * 2. Walk the `prompt_order` for character_id 100001 (user-prompt order)
 *    to determine sequence and default enabled states
 * 3. Filter out comment-only nodes (no content after macro resolution)
 * 4. Return ordered nodes ready for DB insertion, plus filtering stats
 *
 * @param raw - Parsed SillyTavern preset JSON
 * @returns Parse result with nodes and stats, or null if the preset is invalid
 */
function parsePresetNodes(raw: RawSTPreset): ParseResult | null {
	const prompts = raw.prompts;
	if (!Array.isArray(prompts) || prompts.length === 0) {
		return null;
	}

	// 1. Build lookup from prompts array: identifier → node definition
	const promptMap = new Map<string, RawSTPromptNode>();
	for (const prompt of prompts) {
		if (prompt.identifier) {
			promptMap.set(prompt.identifier, prompt);
		}
	}

	// 2. Find the user-prompt order (character_id 100001)
	//    Falls back to character_id 100000 (system prompt order) if 100001 is missing
	const promptOrders = raw.prompt_order;
	let orderEntries: RawSTPromptOrderEntry[] | null = null;

	if (Array.isArray(promptOrders)) {
		const userOrder = promptOrders.find((po) => po.character_id === 100001);
		const systemOrder = promptOrders.find((po) => po.character_id === 100000);
		orderEntries = userOrder?.order ?? systemOrder?.order ?? null;
	}

	// 3. If no prompt_order found, fall back to prompts array order
	if (!orderEntries) {
		orderEntries = prompts.map((p) => ({
			identifier: p.identifier,
			enabled: p.enabled !== false,
		}));
	}

	// 4. Walk the order and build nodes, tracking filtering stats
	const nodes: Omit<StPresetNodeRow, "node_id" | "preset_id">[] = [];
	let nodeOrder = 0;
	let commentOnlySkipped = 0;
	let disabledByPreset = 0;

	for (const entry of orderEntries) {
		const prompt = promptMap.get(entry.identifier);
		if (!prompt) continue;

		const content = prompt.content ?? "";
		const isMarker = prompt.marker === true;

		// Skip comment-only nodes (no usable content after macro resolution)
		if (!isMarker && isCommentOnly(content)) {
			commentOnlySkipped++;
			continue;
		}

		// Track nodes disabled by the preset's prompt_order
		if (!isMarker && !entry.enabled) {
			disabledByPreset++;
		}

		nodes.push({
			identifier: prompt.identifier,
			name: prompt.name ?? prompt.identifier,
			role: prompt.role ?? "system",
			content,
			is_marker: isMarker,
			is_enabled: entry.enabled,
			node_order: nodeOrder++,
			injection_position: prompt.injection_position ?? 0,
			injection_depth: prompt.injection_depth ?? 4,
			injection_order: prompt.injection_order ?? 100,
		});
	}

	if (nodes.length === 0) return null;
	return { nodes, commentOnlySkipped, disabledByPreset };
}

// ─── Execution ───────────────────────────────────────────────────────

/**
 * Execute /stpreset upload.
 * Downloads the attached JSON file, validates it as a SillyTavern preset,
 * parses prompt nodes from the prompt_order, and stores the preset + nodes
 * in the database for this server.
 *
 * @param _client - Discord client instance
 * @param interaction - Command interaction
 * @param userData - User data from database
 * @param locale - User's preferred locale
 */
export async function execute(
	_client: Client,
	interaction: ChatInputCommandInteraction,
	userData: UserRow,
	locale: string,
): Promise<void> {
	// 1. Verify server setup
	const serverId = interaction.guild?.id ?? interaction.user.id;
	const tomoriState = await getCachedTomoriState(serverId);
	if (!tomoriState) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "general.errors.tomori_not_setup_title",
			descriptionKey: "general.errors.tomori_not_setup_description",
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 2. Get and validate the attachment
	const attachment = interaction.options.getAttachment("file", true);
	const validation = validateAttachment(attachment);
	if (!validation.isValid) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.stpreset.upload.invalid_file_title",
			descriptionKey: `commands.stpreset.upload.${validation.errorKey}`,
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 3. Check file size before downloading
	const maxSizeBytes = MAX_PRESET_FILE_SIZE_MB * 1024 * 1024;
	if (attachment.size && attachment.size > maxSizeBytes) {
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.stpreset.upload.file_too_large_title",
			descriptionKey: "commands.stpreset.upload.file_too_large_description",
			descriptionVars: { max_size: MAX_PRESET_FILE_SIZE_MB.toString() },
			color: ColorCode.ERROR,
			flags: MessageFlags.Ephemeral,
		});
		return;
	}

	// 4. Defer reply (download + parsing may take a moment)
	await interaction.deferReply({ flags: MessageFlags.Ephemeral });

	try {
		// 5. Download the file safely
		const downloadResult = await safeDownload(attachment.url, {
			maxSizeMB: MAX_PRESET_FILE_SIZE_MB,
			timeoutMs: 15000,
			knownSize: attachment.size,
		});

		if (!downloadResult.success || !downloadResult.buffer) {
			await interaction.editReply({
				content: localizer(locale, "commands.stpreset.upload.download_failed"),
			});
			return;
		}

		// 6. Parse the JSON
		let rawPreset: RawSTPreset;
		try {
			rawPreset = JSON.parse(downloadResult.buffer.toString("utf-8"));
		} catch {
			await interaction.editReply({
				content: localizer(locale, "commands.stpreset.upload.invalid_json"),
			});
			return;
		}

		// 7. Validate it looks like a SillyTavern preset (must have prompts array)
		if (!rawPreset.prompts || !Array.isArray(rawPreset.prompts)) {
			await interaction.editReply({
				content: localizer(locale, "commands.stpreset.upload.not_a_preset"),
			});
			return;
		}

		// 8. Parse nodes from the preset
		const parseResult = parsePresetNodes(rawPreset);
		if (!parseResult) {
			await interaction.editReply({
				content: localizer(locale, "commands.stpreset.upload.no_nodes"),
			});
			return;
		}

		const { nodes, commentOnlySkipped, disabledByPreset } = parseResult;

		// 9. Derive preset name from filename
		const presetName = derivePresetName(attachment.name ?? "Unnamed Preset");

		// 10. Insert into database
		const preset = await insertPresetWithNodes(
			tomoriState.server_id,
			presetName,
			rawPreset,
			nodes,
		);

		if (!preset) {
			await interaction.editReply({
				content: localizer(locale, "general.errors.unknown_error_description"),
			});
			return;
		}

		// 11. Activate the newly uploaded preset (deactivates any previously active preset)
		if (preset.preset_id) {
			await setActivePreset(tomoriState.server_id, preset.preset_id);
		}

		// 12. Count node types for the summary
		const markerCount = nodes.filter((n) => n.is_marker).length;
		const toggleableCount = nodes.filter((n) => !n.is_marker).length;
		const enabledCount = nodes.filter((n) => n.is_enabled && !n.is_marker).length;

		// 13. Build filtering notes for the success embed
		const filterNotes: string[] = [];
		if (commentOnlySkipped > 0) {
			filterNotes.push(
				localizer(locale, "commands.stpreset.upload.note_comment_only", {
					count: commentOnlySkipped.toString(),
				}),
			);
		}
		if (disabledByPreset > 0) {
			filterNotes.push(
				localizer(locale, "commands.stpreset.upload.note_disabled_by_preset", {
					count: disabledByPreset.toString(),
				}),
			);
		}
		const notes = filterNotes.length > 0 ? filterNotes.join("\n") : "";

		// 14. Success response
		await replyInfoEmbed(interaction, locale, {
			titleKey: "commands.stpreset.upload.success_title",
			descriptionKey: "commands.stpreset.upload.success_description",
			descriptionVars: {
				name: presetName,
				total: nodes.length.toString(),
				markers: markerCount.toString(),
				toggleable: toggleableCount.toString(),
				enabled: enabledCount.toString(),
				notes,
			},
			color: ColorCode.SUCCESS,
		});

		log.success(
			`[ST Preset Upload] "${presetName}" uploaded for server ${serverId} — ${nodes.length} nodes (${toggleableCount} toggleable, ${markerCount} markers, ${commentOnlySkipped} comment-only skipped, ${disabledByPreset} disabled by preset)`,
		);
	} catch (error) {
		const context: ErrorContext = {
			userId: userData.user_id,
			serverId: null,
			tomoriId: null,
			errorType: "CommandExecutionError",
			metadata: { command: "stpreset upload" },
		};
		await log.error("Error executing /stpreset upload", error as Error, context);

		await interaction.editReply({
			content: localizer(locale, "general.errors.unknown_error_description"),
		});
	}
}
