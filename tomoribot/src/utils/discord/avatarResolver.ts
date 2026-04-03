import type { ToolContext } from "@/types/tool/interfaces";
import type { Webhook } from "discord.js";
import { getCachedAllPersonas } from "@/utils/cache/tomoriStateCache";
import { log } from "@/utils/misc/logger";
import { resolvePersonaAvatarPublicUrl } from "@/utils/storage/avatarStorage";

export type ResolvedAvatarData = {
  sourceType: "user" | "webhook" | "persona";
  username: string;
  avatarUrl: string;
  serverNickname?: string;
};

type AvatarResolverOptions = {
  forceStatic: boolean;
};

const DEFAULT_AVATAR_RESOLVER_OPTIONS: AvatarResolverOptions = {
  forceStatic: true,
};

function isNotFoundError(error: Error): boolean {
  return (
    error.message.includes("Unknown User") ||
    error.message.includes("Unknown Webhook") ||
    error.message.includes("Unknown Message") ||
    error.message.includes("not found")
  );
}

function parsePersonaIdentifier(id: string): number | null {
  const trimmed = id.trim();
  const prefixed = /^persona:(\d+)$/i.exec(trimmed);
  const rawNumeric = /^\d{1,10}$/.test(trimmed) ? trimmed : null;
  const candidate = prefixed?.[1] ?? rawNumeric;
  if (!candidate) return null;

  const parsed = Number.parseInt(candidate, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeAvatarTargetId(id: string, context: ToolContext): string {
  const trimmed = id.trim();
  const activePersonaId = context.tomoriState.tomori_id;
  if (activePersonaId == null) {
    return trimmed;
  }

  if (trimmed.toLowerCase() === "self") {
    return `persona:${activePersonaId}`;
  }

  const botUserId = context.client.user?.id;
  if (botUserId && trimmed === botUserId) {
    log.info(
      `[Avatar Resolver] Remapped bot user ID ${trimmed} to active persona persona:${activePersonaId}`,
    );
    return `persona:${activePersonaId}`;
  }

  return trimmed;
}

type WebhookFetchCapableChannel = {
  id: string;
  fetchWebhooks: () => Promise<
    import("discord.js").Collection<string, Webhook>
  >;
};

function isWebhookFetchCapableChannel(
  channel: unknown,
): channel is WebhookFetchCapableChannel {
  if (typeof channel !== "object" || channel === null) {
    return false;
  }

  if (!("fetchWebhooks" in channel)) {
    return false;
  }

  return (
    typeof (channel as { fetchWebhooks?: unknown }).fetchWebhooks === "function"
  );
}

function buildWebhookAvatarData(
  webhook: Webhook,
  forceStatic: boolean,
  personaAvatarUrl?: string,
  fallbackBotAvatarUrl?: string,
): ResolvedAvatarData | null {
  const avatarUrl =
    webhook.avatarURL({
      size: 1024,
      extension: "png",
      forceStatic,
    }) ??
    personaAvatarUrl ??
    fallbackBotAvatarUrl;

  if (!avatarUrl) {
    return null;
  }

  return {
    sourceType: "webhook",
    username: webhook.name ?? `Webhook ${webhook.id}`,
    avatarUrl,
  };
}

async function resolveUserAvatar(
  id: string,
  context: ToolContext,
  options: AvatarResolverOptions,
): Promise<ResolvedAvatarData> {
  const user = await context.client.users.fetch(id);
  let avatarUrl: string;
  let serverNickname: string | undefined;

  if (context.guildId) {
    const guild = context.client.guilds.cache.get(context.guildId);
    if (guild) {
      const member = await guild.members.fetch(id).catch(() => null);
      if (member) {
        avatarUrl = member.displayAvatarURL({
          size: 1024,
          extension: "png",
          forceStatic: options.forceStatic,
        });
        serverNickname = member.nickname ?? undefined;
      } else {
        avatarUrl = user.displayAvatarURL({
          size: 1024,
          extension: "png",
          forceStatic: options.forceStatic,
        });
      }
    } else {
      avatarUrl = user.displayAvatarURL({
        size: 1024,
        extension: "png",
        forceStatic: options.forceStatic,
      });
    }
  } else {
    avatarUrl = user.displayAvatarURL({
      size: 1024,
      extension: "png",
      forceStatic: options.forceStatic,
    });
  }

  return {
    sourceType: "user",
    username: user.username,
    avatarUrl,
    serverNickname,
  };
}

async function resolveWebhookAvatarFromChannel(
  channel: WebhookFetchCapableChannel,
  id: string,
): Promise<Webhook | null> {
  try {
    const webhooks = await channel.fetchWebhooks();
    return webhooks.get(id) ?? null;
  } catch (error) {
    log.warn(
      `[Avatar Resolver] Failed to fetch webhooks for channel ${channel.id} while resolving ${id}`,
      error,
    );
    return null;
  }
}

async function resolveWebhookAvatar(
  id: string,
  context: ToolContext,
  options: AvatarResolverOptions,
): Promise<ResolvedAvatarData | null> {
  const fallbackBotAvatarUrl = context.client.user?.displayAvatarURL({
    size: 1024,
    extension: "png",
    forceStatic: options.forceStatic,
  });

  if (context.webhook?.id === id) {
    const fromContext = buildWebhookAvatarData(
      context.webhook,
      options.forceStatic,
      context.personaAvatarUrl,
      fallbackBotAvatarUrl,
    );
    if (fromContext) {
      return fromContext;
    }
  }

  if (isWebhookFetchCapableChannel(context.channel)) {
    const channelWebhook = await resolveWebhookAvatarFromChannel(
      context.channel,
      id,
    );
    if (channelWebhook) {
      const fromChannel = buildWebhookAvatarData(
        channelWebhook,
        options.forceStatic,
        context.personaAvatarUrl,
        fallbackBotAvatarUrl,
      );
      if (fromChannel) {
        return fromChannel;
      }
    }
  }

  const directWebhook = await context.client.fetchWebhook(id).catch(() => null);
  if (directWebhook) {
    const directResult = buildWebhookAvatarData(
      directWebhook,
      options.forceStatic,
      context.personaAvatarUrl,
      fallbackBotAvatarUrl,
    );
    if (directResult) {
      return directResult;
    }
  }

  if (!context.guildId) {
    return null;
  }

  const guild = context.client.guilds.cache.get(context.guildId);
  if (!guild) {
    return null;
  }

  for (const guildChannel of guild.channels.cache.values()) {
    if (!isWebhookFetchCapableChannel(guildChannel)) {
      continue;
    }

    const webhook = await resolveWebhookAvatarFromChannel(guildChannel, id);
    if (!webhook) {
      continue;
    }

    const fromGuildScan = buildWebhookAvatarData(
      webhook,
      options.forceStatic,
      context.personaAvatarUrl,
      fallbackBotAvatarUrl,
    );
    if (fromGuildScan) {
      return fromGuildScan;
    }
  }

  return null;
}

async function resolvePersonaAvatar(
  personaId: number,
  context: ToolContext,
  options: AvatarResolverOptions,
): Promise<ResolvedAvatarData | null> {
  const guildId = context.guildId;
  if (!guildId) {
    return null;
  }

  const allPersonas = await getCachedAllPersonas(guildId).catch((error) => {
    log.warn(
      `[Avatar Resolver] Failed to load personas for guild ${guildId} while resolving persona:${personaId}`,
      error,
    );
    return [];
  });
  const persona = allPersonas.find((entry) => entry.tomori_id === personaId);
  if (!persona) {
    return null;
  }

  let avatarUrl: string | null = null;

  if (persona.is_alter) {
    avatarUrl = resolvePersonaAvatarPublicUrl(persona.webhook_avatar_url) ?? null;
  } else {
    const guild = context.client.guilds.cache.get(guildId);
    avatarUrl =
      guild?.iconURL({
        size: 1024,
        extension: "png",
        forceStatic: options.forceStatic,
      }) ??
      resolvePersonaAvatarPublicUrl(persona.webhook_avatar_url) ??
      null;
  }

  if (!avatarUrl && context.personaUsername === persona.tomori_nickname) {
    avatarUrl = context.personaAvatarUrl ?? null;
  }

  if (
    !avatarUrl &&
    context.webhook &&
    context.personaUsername === persona.tomori_nickname
  ) {
    avatarUrl =
      context.webhook.avatarURL({
        size: 1024,
        extension: "png",
        forceStatic: options.forceStatic,
      }) ?? null;
  }

  if (!avatarUrl) {
    avatarUrl =
      context.client.user?.displayAvatarURL({
        size: 1024,
        extension: "png",
        forceStatic: options.forceStatic,
      }) ?? null;
  }

  if (!avatarUrl) {
    return null;
  }

  return {
    sourceType: "persona",
    username: persona.tomori_nickname,
    avatarUrl,
  };
}

export async function resolveAvatarByDiscordId(
  id: string,
  context: ToolContext,
  options?: Partial<AvatarResolverOptions>,
): Promise<ResolvedAvatarData> {
  const resolvedOptions: AvatarResolverOptions = {
    ...DEFAULT_AVATAR_RESOLVER_OPTIONS,
    ...options,
  };
  const normalizedId = normalizeAvatarTargetId(id, context);

  const personaId = parsePersonaIdentifier(normalizedId);
  if (personaId !== null) {
    const personaAvatar = await resolvePersonaAvatar(
      personaId,
      context,
      resolvedOptions,
    );
    if (personaAvatar) {
      log.info(
        `[Avatar Resolver] Resolved ID ${id} as persona avatar (${personaAvatar.username}) via ${normalizedId}`,
      );
      return personaAvatar;
    }
    throw new Error(`No persona found with tomori_id ${personaId}`);
  }

  try {
    return await resolveUserAvatar(normalizedId, context, resolvedOptions);
  } catch (userError) {
    const userErrorObj =
      userError instanceof Error
        ? userError
        : new Error("Unknown error while resolving user avatar");
    const webhookAvatar = await resolveWebhookAvatar(
      normalizedId,
      context,
      resolvedOptions,
    );

    if (webhookAvatar) {
      log.info(
        `[Avatar Resolver] Resolved ID ${id} as webhook avatar (${webhookAvatar.username}) via ${normalizedId}`,
      );
      return webhookAvatar;
    }

    if (!isNotFoundError(userErrorObj)) {
      throw new Error(
        `${userErrorObj.message} (and no matching webhook was found for ID ${normalizedId})`,
      );
    }

    throw new Error(`No Discord user or webhook found with ID ${normalizedId}`);
  }
}
