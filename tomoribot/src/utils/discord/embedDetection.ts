/**
 * Shared embed detection utilities for identifying bot-generated system embeds.
 * Extracts the refresh/reset marker detection logic from tomoriChat.ts so it
 * can be reused by the history fetcher and other utilities.
 */

import type { Embed } from "discord.js";
import { localizer, getSupportedLocales } from "@/utils/text/localizer";

/**
 * Checks whether a single embed is a "refresh marker" — an embed that signals
 * a conversation reset or compact-refresh boundary.
 *
 * Matches the following localizer keys across all supported locales:
 * - `commands.tool.refresh.title` (conversation reset)
 * - `commands.tool.compact.summary_title_refreshed` (compact summary refresh)
 * - `commands.tool.compact.roleplay_scene_title_refreshed` (compact scene refresh)
 *
 * @param embed - A Discord embed to check
 * @returns True if the embed is a refresh/reset marker
 */
export function isRefreshMarkerEmbed(embed: Embed): boolean {
  const title = embed.title;
  if (!title) return false;

  for (const supportedLocale of getSupportedLocales()) {
    // 1. Check for conversation reset title
    const resetTitle = localizer(
      supportedLocale,
      "commands.tool.refresh.title",
    );
    if (title === resetTitle) return true;

    // 2. Check for compact summary refreshed title
    const compactSummaryRefreshed = localizer(
      supportedLocale,
      "commands.tool.compact.summary_title_refreshed",
    );
    if (title === compactSummaryRefreshed) return true;

    // 3. Check for compact roleplay scene refreshed title
    const compactSceneRefreshed = localizer(
      supportedLocale,
      "commands.tool.compact.roleplay_scene_title_refreshed",
    );
    if (title === compactSceneRefreshed) return true;
  }

  return false;
}

/**
 * Checks whether any embed in an array is a refresh marker.
 *
 * @param embeds - Array of Discord embeds from a message
 * @returns True if at least one embed is a refresh/reset marker
 */
export function messageContainsRefreshMarker(embeds: Embed[]): boolean {
  return embeds.some(isRefreshMarkerEmbed);
}
