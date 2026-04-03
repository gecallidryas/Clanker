/**
 * Cross-Channel Message Tool
 * Allows the AI to send an instant, natural message to a different channel in the same server.
 * Includes an optional "boomerang" mechanism that triggers a follow-up generation back in the
 * source channel to report what happened.
 */

import { PermissionFlagsBits } from "discord.js";
import type { GuildTextBasedChannel, Message } from "discord.js";
import { log } from "../../utils/misc/logger";
import {
  BaseTool,
  type ToolContext,
  type ToolResult,
  type ToolParameterSchema,
} from "../../types/tool/interfaces";
import type { StructuredContextItem } from "../../types/misc/context";
import { ContextItemTag } from "../../types/misc/context";
import { isRefreshMarkerEmbed } from "../../utils/discord/embedDetection";

// ─── Boomerang Mechanism ─────────────────────────────────────────────
// Stores pending boomerang data keyed by source channel ID.
// After tomoriChat() completes in the target channel, the source channel
// consumes this data to trigger a separate follow-up generation.

/** Data stored for a pending boomerang report-back */
export interface PendingBoomerang {
  /** Channel ID where the original conversation happened */
  sourceChannelId: string;
  /** Human-readable name of the target channel */
  targetChannelName: string;
  /** Discord ID of the target channel */
  targetChannelId: string;
  /** The task that was dispatched */
  task: string;
  /** Whether the target generation succeeded */
  success: boolean;
  /** Error message if failed */
  error?: string;
  /** Persona ID to use for the boomerang generation */
  personaId?: number;
  /** Recent messages from the target channel (newest first) */
  targetChannelMessages: Array<{
    author: string;
    content: string;
    timestamp: string;
  }>;
}

const pendingBoomerangs = new Map<string, PendingBoomerang>();

/**
 * Consume (retrieve and delete) a pending boomerang for a given channel.
 * Called by tomoriChat after STM storage to check if a follow-up is needed.
 * @param channelId - The channel ID to check for pending boomerangs
 * @returns The boomerang data if one exists, otherwise undefined
 */
export function consumePendingBoomerang(
  channelId: string,
): PendingBoomerang | undefined {
  const boomerang = pendingBoomerangs.get(channelId);
  if (boomerang) {
    pendingBoomerangs.delete(channelId);
  }
  return boomerang;
}

/**
 * Build the injected context items for a boomerang report-back generation.
 * @param boomerang - The boomerang data to format
 * @returns StructuredContextItem array for injection into tomoriChat
 */
export function buildBoomerangContext(
  boomerang: PendingBoomerang,
): StructuredContextItem[] {
  // Format target channel messages for context
  let messagesBlock = "";
  if (boomerang.targetChannelMessages.length > 0) {
    const formatted = boomerang.targetChannelMessages
      .map((m) => `"${m.author}: ${m.content}"`)
      .join("\n");
    // Truncate if total exceeds ~1500 chars to stay within reasonable context size
    messagesBlock =
      formatted.length > 1500
        ? `${formatted.substring(0, 1497)}...`
        : formatted;
  }

  const resultStr = boomerang.success
    ? "Success"
    : `Failed: ${boomerang.error ?? "unknown error"}`;

  let contextText = `[System: You just visited #${boomerang.targetChannelName} to perform a task.\nTask: "${boomerang.task}". Result: ${resultStr}.`;
  if (messagesBlock) {
    contextText += `\nHere is what was happening in #${boomerang.targetChannelName} (last 10 messages, newest first):\n${messagesBlock}`;
  }
  contextText += "\nNow naturally tell the people here what you did or found.]";

  return [
    {
      role: "user",
      parts: [{ type: "text", text: contextText }],
      metadataTag: ContextItemTag.SYSTEM_INSTRUCTION_BLOCK,
    },
  ];
}

// ─── Cross-Channel Message Tool ──────────────────────────────────────

/**
 * Tool for sending an instant, natural message to a different channel in the same server.
 * Unlike create_task, this executes immediately rather than scheduling.
 */
export class CrossChannelMessageTool extends BaseTool {
  name = "cross_channel_message";
  description =
    "Send an instant message to a different channel or thread in the same server. Use this when you want to immediately say something, ask a question, or perform a task in another channel or thread — NOT for scheduled or recurring posts (use create_task for those). You will generate a natural conversational message in the target channel or thread. Optionally enable 'boomerang' to report back to the current channel about what you did.";
  category = "discord" as const;

  parameters: ToolParameterSchema = {
    type: "object",
    properties: {
      channel_id: {
        type: "string",
        description:
          "Discord ID of the target channel or thread to send a message in. At least one of channel_id or channel_name must be provided.",
      },
      channel_name: {
        type: "string",
        description:
          "Name of the target channel (without #). Used as a fallback if channel_id is not provided, or as an alternative lookup method. This matches guild channel names and active thread titles. At least one of channel_id or channel_name must be provided.",
      },
      task: {
        type: "string",
        description:
          "A descriptive task (2-4 sentences) explaining what you should do in the target channel. Be specific about WHAT to say, the TONE to use, and any context from the current conversation that's relevant. This instruction guides your message generation in the target channel.",
      },
      boomerang: {
        type: "boolean",
        description:
          "If true, after sending the message in the target channel, you will automatically generate a follow-up message back in the current channel reporting what you did or found. Useful when someone asked you to go check on or say something in another channel.",
      },
    },
    required: ["task"],
  };

  /**
   * Check if cross-channel message tool is available for the given provider.
   * Excluded for NovelAI (GLM) due to token budget limitations.
   * @param provider - LLM provider name
   * @returns True if provider supports this tool
   */
  isAvailableFor(provider: string): boolean {
    return provider.toLowerCase() !== "novelai";
  }

  /**
   * Execute cross-channel message dispatch.
   * 1. Validates parameters and resolves the target channel
   * 2. Fetches a context message from the target channel
   * 3. Calls tomoriChat() with injected task context
   * 4. Optionally stores boomerang data for follow-up
   * @param args - Tool arguments
   * @param context - Tool execution context
   * @returns Promise resolving to tool result
   */
  async execute(
    args: Record<string, unknown>,
    context: ToolContext,
  ): Promise<ToolResult> {
    // 1. Extract and validate parameters
    const channelIdArg = args.channel_id as string | undefined;
    const channelNameArg = args.channel_name as string | undefined;
    const taskArg = args.task as string;
    const boomerangArg = args.boomerang as boolean | undefined;

    // Validate: at least one channel identifier must be provided
    if (!channelIdArg?.trim() && !channelNameArg?.trim()) {
      return {
        success: false,
        error:
          "At least one of 'channel_id' or 'channel_name' must be provided to identify the target channel.",
        data: {
          status: "cross_channel_failed_missing_channel",
          reason: "No channel identifier provided.",
        },
      };
    }

    // Validate: task must be non-empty
    if (typeof taskArg !== "string" || !taskArg.trim()) {
      return {
        success: false,
        error:
          "The 'task' parameter is required and must be a non-empty string describing what to do in the target channel.",
        data: {
          status: "cross_channel_failed_missing_task",
          reason: "Task is empty or missing.",
        },
      };
    }

    // 2. DM guard — cross-channel only works within a guild
    if (!context.guildId) {
      return {
        success: false,
        error:
          "Cross-channel messaging is only available in server channels, not in DMs.",
        data: {
          status: "cross_channel_failed_dm_context",
          reason: "Cannot use cross-channel messaging in DMs.",
        },
      };
    }

    // 3. Resolve the target channel
    const guild = await context.client.guilds
      .fetch(context.guildId)
      .catch(() => null);
    if (!guild) {
      return {
        success: false,
        error: "Failed to resolve the current server.",
        data: {
          status: "cross_channel_failed_guild_not_found",
          reason: "Could not fetch guild.",
        },
      };
    }

    let targetChannel: GuildTextBasedChannel | null = null;
    const activeThreads = await guild.channels.fetchActiveThreads().catch((error) => {
      log.warn("Cross-channel tool: Failed to fetch active threads", error);
      return null;
    });

    // Try channel_id first
    if (channelIdArg?.trim()) {
      const trimmedId = channelIdArg.trim();
      const fetched = await context.client.channels
        .fetch(trimmedId)
        .catch(() => null);

      // If exact fetch fails, try GLM fuzzy BigInt recovery
      if (!fetched) {
        try {
          const garbledId = BigInt(trimmedId);
          let closestChannelId: string | null = null;
          let smallestDiff = BigInt(1000);
          const candidateIds = new Set<string>(guild.channels.cache.keys());

          if (activeThreads) {
            for (const threadId of activeThreads.threads.keys()) {
              candidateIds.add(threadId);
            }
          }

          for (const chId of candidateIds) {
            const diff =
              garbledId > BigInt(chId)
                ? garbledId - BigInt(chId)
                : BigInt(chId) - garbledId;
            if (diff > 0n && diff < smallestDiff) {
              smallestDiff = diff;
              closestChannelId = chId;
            }
          }

          if (closestChannelId) {
            log.info(
              `Cross-channel tool: Correcting garbled channel ID "${trimmedId}" → "${closestChannelId}" (diff: ${smallestDiff})`,
            );
            const corrected = await context.client.channels
              .fetch(closestChannelId)
              .catch(() => null);
            if (corrected?.isTextBased() && !corrected.isDMBased()) {
              targetChannel = corrected as GuildTextBasedChannel;
            }
          }
        } catch {
          // BigInt parsing failed — skip fuzzy match
        }
      } else if (fetched.isTextBased() && !fetched.isDMBased()) {
        targetChannel = fetched as GuildTextBasedChannel;
      }
    }

    // Fallback to channel_name or thread title lookup
    if (!targetChannel && channelNameArg?.trim()) {
      const nameLower = channelNameArg.trim().toLowerCase();
      const found = guild.channels.cache.find(
        (ch) => ch.name.toLowerCase() === nameLower && ch.isTextBased(),
      );
      if (found?.isTextBased()) {
        targetChannel = found as GuildTextBasedChannel;
      } else if (activeThreads) {
        const matchingThread = activeThreads.threads.find(
          (thread) => thread.name.toLowerCase() === nameLower,
        );
        if (matchingThread?.isTextBased()) {
          targetChannel = matchingThread as GuildTextBasedChannel;
        }
      }
    }

    if (!targetChannel) {
      return {
        success: false,
        error: `Could not find a text channel or thread matching ${channelIdArg ? `ID "${channelIdArg}"` : `name "${channelNameArg}"`} in this server.`,
        data: {
          status: "cross_channel_failed_channel_not_found",
          reason: "Target channel or thread not found or not a text-based channel.",
        },
      };
    }

    // Verify target is in the same guild
    if (
      !("guildId" in targetChannel) ||
      targetChannel.guildId !== context.guildId
    ) {
      return {
        success: false,
        error: "The target channel or thread does not belong to this server.",
        data: {
          status: "cross_channel_failed_wrong_guild",
          reason: "Target channel or thread is in a different guild.",
        },
      };
    }

    // 4. Same-channel guard
    if (targetChannel.id === context.channel.id) {
      return {
        success: false,
        error:
          "Cannot send a cross-channel message to the same channel or thread you are already in. Just speak normally instead.",
        data: {
          status: "cross_channel_failed_same_channel",
          reason: "Target channel or thread is the same as source.",
        },
      };
    }

    // 5. Permission check — bot must have ViewChannel + (SendMessages or SendMessagesInThreads)
    const botMember = guild.members.cache.get(context.client.user?.id ?? "");
    if (botMember && "permissionsFor" in targetChannel) {
      const perms = targetChannel.permissionsFor(botMember);

      // Check ViewChannel permission (required for all text-based channels)
      if (perms && !perms.has(PermissionFlagsBits.ViewChannel)) {
        return {
          success: false,
          error: `I don't have permission to view #${targetChannel.name}.`,
          data: {
            status: "cross_channel_failed_no_view_permission",
            reason: "Missing ViewChannel permission.",
          },
        };
      }

      // Check if target is a thread
      const isThread =
        "isThread" in targetChannel &&
        typeof targetChannel.isThread === "function" &&
        targetChannel.isThread();

      // Check send permission: SendMessages for channels, SendMessagesInThreads for threads
      const sendPermission = isThread
        ? PermissionFlagsBits.SendMessagesInThreads
        : PermissionFlagsBits.SendMessages;

      if (perms && !perms.has(sendPermission)) {
        const permissionName = isThread ? "SendMessagesInThreads" : "SendMessages";
        const targetName = isThread
          ? `thread "${targetChannel.name}"`
          : `#${targetChannel.name}`;
        return {
          success: false,
          error: `I don't have permission to send messages in ${targetName}.`,
          data: {
            status: isThread
              ? "cross_channel_failed_no_send_in_threads_permission"
              : "cross_channel_failed_no_send_permission",
            reason: `Missing ${permissionName} permission.`,
          },
        };
      }
    }

    // 6. Fetch last message from target channel (context for tomoriChat)
    let lastMessage: Message | undefined;
    try {
      const messages = await targetChannel.messages.fetch({ limit: 1 });
      lastMessage = messages.first();
    } catch (fetchError) {
      log.warn(
        `Cross-channel tool: Failed to fetch last message from #${targetChannel.name}:`,
        fetchError,
      );
    }

    // Seed a braille blank if channel is empty (same pattern as reminderTimer)
    if (!lastMessage && "send" in targetChannel) {
      try {
        lastMessage = await targetChannel.send({
          content: "\u2800",
        });
        log.info(
          `Cross-channel tool: Seeded placeholder message in #${targetChannel.name}`,
        );
      } catch (sendError) {
        log.warn(
          `Cross-channel tool: Failed to seed placeholder in #${targetChannel.name}:`,
          sendError,
        );
      }
    }

    if (!lastMessage) {
      return {
        success: false,
        error: `Could not fetch or create a context message in #${targetChannel.name}.`,
        data: {
          status: "cross_channel_failed_no_context_message",
          reason: "No messages available in target channel.",
        },
      };
    }

    // 7. Build injected context with the task instruction
    const taskInjection: StructuredContextItem = {
      role: "user",
      parts: [
        {
          type: "text",
          text: `[System: You have been dispatched to this channel to perform a task.\nTask: "${taskArg.trim()}".\nComplete this task naturally as a conversational message.]`,
        },
      ],
      metadataTag: ContextItemTag.SYSTEM_INSTRUCTION_BLOCK,
    };

    // 8. Suppress self-reply to avoid loop
    const { suppressNextSelfReply } = await import(
      "../../events/messageCreate/tomoriChat"
    );
    suppressNextSelfReply(targetChannel.id);

    // 9. Call tomoriChat in the target channel
    const tomoriChat = (await import("../../events/messageCreate/tomoriChat"))
      .default;

    const sourcePersonaId = context.tomoriState.tomori_id ?? undefined;

    try {
      await tomoriChat(
        context.client,
        lastMessage,
        false, // isFromQueue
        true, // isManuallyTriggered
        false, // forceReason
        undefined, // reasoningQuery
        undefined, // llmOverrideCodename
        false, // isStopResponse
        0, // retryCount
        false, // skipLock
        undefined, // reminderRecipientID
        undefined, // reminderData
        sourcePersonaId, // selectedPersonaId — same persona visits target
        false, // isPersonaJob
        false, // isUserImpersonation
        undefined, // impersonatedUserId
        "system", // textQuotaSource — system-triggered
        undefined, // textQuotaTriggerKey
        undefined, // textQuotaUserDiscId
        undefined, // manualSystemPrompt
        undefined, // manualPrefill
        undefined, // naiContinuationPrefill
        undefined, // emptyResponseFinishReason
        [taskInjection], // injectedContextItems
      );

      log.success(
        `Cross-channel tool: Successfully dispatched to #${targetChannel.name} (task: "${taskArg.trim().substring(0, 80)}...")`,
      );

      // 10. Handle boomerang — store data for follow-up generation in source channel
      if (boomerangArg) {
        // Fetch last 10 messages from target channel (including the one the bot just sent),
        // but respect refresh embed boundaries — only include messages after the most recent one
        let targetMessages: Array<{
          author: string;
          content: string;
          timestamp: string;
        }> = [];
        try {
          const recentMessages = await targetChannel.messages.fetch({
            limit: 10,
          });
          // Discord returns newest-first; truncate at refresh embed boundary
          const messagesArray = [...recentMessages.values()];
          const filteredMessages: Message[] = [];
          for (const m of messagesArray) {
            // Stop if we hit a refresh/reset embed — everything before it is stale context
            if (m.embeds.length > 0 && m.embeds.some(isRefreshMarkerEmbed)) {
              log.info(
                `Cross-channel tool: Boomerang message fetch hit refresh embed at ${m.id} — truncating older messages`,
              );
              break;
            }
            filteredMessages.push(m);
          }
          targetMessages = filteredMessages.map((m) => ({
            author: m.author.displayName ?? m.author.username,
            content: m.content || "(no text content)",
            timestamp: m.createdAt.toISOString(),
          }));
        } catch (msgFetchError) {
          log.warn(
            `Cross-channel tool: Failed to fetch target channel messages for boomerang:`,
            msgFetchError,
          );
        }

        pendingBoomerangs.set(context.channel.id, {
          sourceChannelId: context.channel.id,
          targetChannelName: targetChannel.name,
          targetChannelId: targetChannel.id,
          task: taskArg.trim(),
          success: true,
          personaId: sourcePersonaId,
          targetChannelMessages: targetMessages,
        });

        log.info(
          `Cross-channel tool: Boomerang stored for source channel ${context.channel.id} → #${targetChannel.name}`,
        );
      }

      // When boomerang is enabled, end the LLM's current turn immediately.
      // The boomerang mechanism will trigger a separate generation with the actual
      // target channel context, so we must prevent the LLM from fabricating a report here.
      if (boomerangArg) {
        return {
          success: true,
          endTurn: true,
          message: `You visited #${targetChannel.name}, completed your task, and have now returned to this channel to report back.`,
          data: {
            status: "cross_channel_visit_complete",
            target_channel_name: targetChannel.name,
            target_channel_id: targetChannel.id,
            boomerang: true,
            note: `You have already visited #${targetChannel.name} and completed your task there. You are now back in this channel. Report what you found or did.`,
          },
        };
      }

      return {
        success: true,
        message: `Message sent to #${targetChannel.name}.`,
        data: {
          status: "cross_channel_message_sent",
          target_channel_name: targetChannel.name,
          target_channel_id: targetChannel.id,
          boomerang: false,
        },
      };
    } catch (error) {
      log.error(
        `Cross-channel tool: Failed to dispatch to #${targetChannel.name}:`,
        error as Error,
      );

      // Store failed boomerang if requested
      if (boomerangArg) {
        pendingBoomerangs.set(context.channel.id, {
          sourceChannelId: context.channel.id,
          targetChannelName: targetChannel.name,
          targetChannelId: targetChannel.id,
          task: taskArg.trim(),
          success: false,
          error: error instanceof Error ? error.message : "Unknown error",
          personaId: sourcePersonaId,
          targetChannelMessages: [],
        });
      }

      return {
        success: false,
        error: `Failed to send message in #${targetChannel.name}: ${error instanceof Error ? error.message : "Unknown error"}`,
        data: {
          status: "cross_channel_failed_dispatch_error",
          reason: error instanceof Error ? error.message : "Unknown error",
        },
      };
    }
  }
}
