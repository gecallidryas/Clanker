/**
 * Refresh Message Timestamps Tool
 *
 * Triggers a context restart that rebuilds the conversation history with
 * timestamp annotations appended to every message, showing both an absolute
 * UTC time and a relative "X ago" label.
 *
 * This is an on-demand tool — timestamps are not included in context by default
 * to avoid token bloat. The LLM calls this when precise timing information is
 * needed (e.g. "when did Toasty send that message?").
 *
 * Like the media context tools, this tool does not perform the rebuild itself.
 * It returns a `context_restart_with_timestamps` signal that tomoriChat.ts
 * intercepts, then calls buildContext() again with `includeTimestamps: true`.
 */

import {
  BaseTool,
  type ToolContext,
  type ToolResult,
  type ToolParameterSchema,
} from "../../types/tool/interfaces";
import { log } from "../../utils/misc/logger";

export class RefreshMessageTimestampsTool extends BaseTool {
  name = "refresh_message_timestamps";
  description =
    "Rebuild conversation context with timestamps on every message (e.g. 'Feb 28, 2026 14:32 UTC, 3h ago'). Only use this when a user is directly asking WHEN something was said or how long ago, for example 'when did X say that?' or 'how long ago was that message?'. Do NOT use this for general conversation, recalling what was said, summarizing content, or questions about the order of events that can be inferred from context.";
  category = "utility" as const;

  parameters: ToolParameterSchema = {
    type: "object",
    properties: {},
    required: [],
  };

  /**
   * Available for all providers — timestamp annotation is provider-agnostic.
   * @param _provider - LLM provider name (unused)
   * @returns Always true (gating is done in isAvailableForContext)
   */
  isAvailableFor(_provider: string): boolean {
    return true;
  }

  /**
   * Enhanced availability check that disables the tool after it has fired once
   * per turn. Once context is rebuilt with timestamps, calling it again would
   * just restart the context a second time for no gain.
   * @param provider - LLM provider name
   * @param context - Tool context that may contain streaming flags
   * @returns True if tool should be offered to the LLM this turn
   */
  isAvailableForContext(provider: string, context?: ToolContext): boolean {
    if (!this.isAvailableFor(provider)) return false;

    if (context?.streamContext?.disableTimestampContext) {
      log.info(
        "RefreshMessageTimestampsTool: Disabled for this turn — timestamps already added to context",
      );
      return false;
    }

    return true;
  }

  /**
   * Signal tomoriChat to rebuild context with timestamp annotations.
   * Returns a context restart signal; no actual context modification is done here.
   * @param _args - No parameters required
   * @param context - Tool execution context
   * @returns Restart signal or early-out if already fired this turn
   */
  async execute(
    _args: Record<string, unknown>,
    context: ToolContext,
  ): Promise<ToolResult> {
    // Defense-in-depth guard: block if already fired this turn
    if (context.streamContext?.disableTimestampContext) {
      log.info(
        "[RefreshMessageTimestampsTool] Execution blocked — timestamps already added this turn",
      );
      return {
        success: false,
        message: "Message timestamps were already added to context this turn.",
      };
    }

    log.info(
      "[RefreshMessageTimestampsTool] Signalling context restart with timestamp annotations",
    );

    return {
      success: true,
      message: "Rebuilding context with message timestamps...",
      data: {
        type: "context_restart_with_timestamps",
      },
    };
  }
}
