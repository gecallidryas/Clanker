/**
 * Channel history fetcher for the /teach history command.
 * Fetches messages backward from the latest message in a channel,
 * stopping at a refresh marker or the configured message limit.
 */

import type {
  TextBasedChannel,
  Message,
  Collection,
  Snowflake,
} from "discord.js";
import { messageContainsRefreshMarker } from "@/utils/discord/embedDetection";
import { log } from "@/utils/misc/logger";

/** Maximum messages Discord allows per fetch call */
const DISCORD_FETCH_BATCH_SIZE = 100;

/** Result of a history fetch operation */
export interface FetchedHistoryResult {
  /** Messages in chronological order (oldest first) */
  messages: Message[];

  /** Total number of messages fetched before filtering */
  totalFetched: number;

  /** Whether the fetch stopped because a refresh marker was found */
  hitRefreshMarker: boolean;

  /** Whether the fetch stopped because the max message limit was reached */
  hitMaxLimit: boolean;
}

/**
 * Fetches channel messages backward from the latest position until a refresh
 * marker embed is found or the maximum message limit is reached.
 *
 * Messages are returned in chronological order (oldest first).
 * The refresh marker message itself is NOT included in the results.
 *
 * @param channel - The Discord text channel to fetch from
 * @param maxMessages - Maximum number of messages to fetch
 * @returns Fetch result with messages, count, and stop reason
 */
export async function fetchHistoryUntilMarker(
  channel: TextBasedChannel,
  maxMessages: number,
): Promise<FetchedHistoryResult> {
  const accumulated: Message[] = [];
  let lastMessageId: string | undefined;
  let hitRefreshMarker = false;
  let hitMaxLimit = false;
  let totalFetched = 0;

  while (accumulated.length < maxMessages) {
    // 1. Calculate how many more messages we need
    const remaining = maxMessages - accumulated.length;
    const batchSize = Math.min(remaining, DISCORD_FETCH_BATCH_SIZE);

    // 2. Fetch a batch of messages (newest first from Discord API)
    const fetchOptions: { limit: number; before?: string } = {
      limit: batchSize,
    };
    if (lastMessageId) {
      fetchOptions.before = lastMessageId;
    }

    let batch: Collection<Snowflake, Message>;
    try {
      batch = await channel.messages.fetch(fetchOptions);
    } catch (fetchError) {
      log.warn(
        `Failed to fetch messages from channel ${channel.id}: ${fetchError}`,
      );
      break;
    }

    // 3. If no more messages, stop
    if (batch.size === 0) break;

    totalFetched += batch.size;

    // 4. Process batch (Discord returns newest first, so iterate in order)
    for (const [, msg] of batch) {
      // Check for refresh marker in this message's embeds
      if (msg.embeds.length > 0 && messageContainsRefreshMarker(msg.embeds)) {
        hitRefreshMarker = true;
        break;
      }

      accumulated.push(msg);

      if (accumulated.length >= maxMessages) {
        hitMaxLimit = true;
        break;
      }
    }

    // 5. Stop if we hit a marker or limit
    if (hitRefreshMarker || hitMaxLimit) break;

    // 6. Update cursor to the oldest message in this batch for next iteration
    const batchArray = [...batch.values()];
    lastMessageId = batchArray[batchArray.length - 1].id;

    // 7. If batch was smaller than requested, we've exhausted the channel
    if (batch.size < batchSize) break;
  }

  // Reverse to chronological order (oldest first)
  accumulated.reverse();

  return {
    messages: accumulated,
    totalFetched,
    hitRefreshMarker,
    hitMaxLimit,
  };
}
