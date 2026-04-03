import type {
  ChatInputCommandInteraction,
  ButtonInteraction,
  ModalSubmitInteraction,
  Client,
  SlashCommandSubcommandBuilder,
} from "discord.js";
import { MessageFlags } from "discord.js";
import { sql } from "@/utils/db/client";
import { localizer } from "../../utils/text/localizer";
import { log, ColorCode } from "../../utils/misc/logger";
import {
  replyInfoEmbed,
  replyPaginatedPersonaChoicesV2,
  promptWithPaginatedModal,
  safeSelectOptionText,
} from "../../utils/discord/interactionHelper";
import { getCachedTomoriState } from "../../utils/cache/tomoriStateCache";
import type { UserRow, ErrorContext, TomoriState } from "../../types/db/schema";
import type { SelectOption } from "../../types/discord/modal";
import {
  deleteReminderById,
  loadAllPersonasForServer,
} from "../../utils/db/dbRead";
import {
  formatTimeWithOffset,
  formatUTCOffset,
} from "../../utils/text/timezoneHelper";
import { isBridgeUserId } from "../../utils/bridge";

// Rule 20: Constants for static values at the top
const MODAL_CUSTOM_ID = "forget_reminder_modal";
const REMINDER_SELECT_ID = "reminder_select";
type ReminderSelectionRow = {
  reminder_id: number;
  reminder_purpose: string;
  reminder_time: Date;
  repetition_interval_hours: number | null;
  channel_disc_id: string;
  created_by_user_id: number | null;
  created_by_nickname: string | null;
  user_discord_id: string;
  user_nickname: string;
};

/**
 * Helper function to perform reminder removal from database
 * @param reminderToRemove - Reminder data to remove
 * @param replyInteraction - Interaction to reply to (can be modal or pagination)
 * @param locale - User locale
 */
async function performReminderRemoval(
  reminderToRemove: { reminder_id: number; reminder_purpose: string },
  replyInteraction:
    | ChatInputCommandInteraction
    | ButtonInteraction
    | ModalSubmitInteraction,
  locale: string,
): Promise<void> {
  const deleted = await deleteReminderById(reminderToRemove.reminder_id);

  if (!deleted) {
    await replyInfoEmbed(replyInteraction, locale, {
      titleKey: "general.errors.operation_failed_title",
      descriptionKey: "general.errors.operation_failed_description",
      color: ColorCode.ERROR,
    });
    return;
  }

  log.success(
    `Deleted reminder ${reminderToRemove.reminder_id} (${reminderToRemove.reminder_purpose.slice(0, 60)}...)`,
  );

  await replyInfoEmbed(replyInteraction, locale, {
    titleKey: "commands.forget.reminder.success_title",
    descriptionKey: "commands.forget.reminder.success_description",
    descriptionVars: {
      reminder_purpose:
        reminderToRemove.reminder_purpose.length > 80
          ? `${reminderToRemove.reminder_purpose.slice(0, 77)}...`
          : reminderToRemove.reminder_purpose,
    },
    color: ColorCode.SUCCESS,
  });
}

// Rule 21: Configure the subcommand
export const configureSubcommand = (
  subcommand: SlashCommandSubcommandBuilder,
) =>
  subcommand
    .setName("reminder")
    .setDescription(localizer("en-US", "commands.forget.reminder.description"));

/**
 * Removes a reminder for the user using a paginated modal.
 * @param _client - Discord client instance
 * @param interaction - Command interaction
 * @param userData - User data from database
 * @param locale - Locale of the interaction
 */
export async function execute(
  _client: Client,
  interaction: ChatInputCommandInteraction,
  userData: UserRow,
  locale: string,
): Promise<void> {
  // 1. Ensure command is run in a valid channel context
  if (!interaction.channel) {
    await replyInfoEmbed(interaction, locale, {
      titleKey: "general.errors.channel_only_title",
      descriptionKey: "general.errors.channel_only_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
    return;
  }

  let tomoriState: TomoriState | null = null;
  let targetTomoriId: number | null = null;
  let targetIsAlter = false;
  let personaSelectionInteraction: ButtonInteraction | null = null;

  try {
    tomoriState = await getCachedTomoriState(
      interaction.guild?.id ?? interaction.user.id,
    );
    if (!tomoriState) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    const hasManagePermission =
      interaction.memberPermissions?.has("ManageGuild") ?? false;

    const allPersonas = await loadAllPersonasForServer(
      interaction.guild?.id ?? interaction.user.id,
    );
    if (allPersonas.length === 0) {
      await replyInfoEmbed(interaction, locale, {
        titleKey: "general.errors.tomori_not_setup_title",
        descriptionKey: "general.errors.tomori_not_setup_description",
        color: ColorCode.ERROR,
        flags: MessageFlags.Ephemeral,
      });
      return;
    }

    while (true) {
      const personaSelection = await replyPaginatedPersonaChoicesV2(
        interaction,
        locale,
        {
          personas: allPersonas,
          color: ColorCode.INFO,
          preserveSelectedInteraction: true,
          onSelect: async () => {},
        },
      );

      if (!personaSelection.success) {
        if (personaSelection.reason === "cancelled") return;
        continue;
      }
      if (
        personaSelection.selectedIndex === undefined ||
        !personaSelection.interaction
      ) {
        return;
      }

      personaSelectionInteraction = personaSelection.interaction;
      const selectedPersona =
        allPersonas[personaSelection.selectedIndex] ?? null;
      if (!selectedPersona?.tomori_id) {
        await replyInfoEmbed(personaSelectionInteraction, locale, {
          titleKey: "general.errors.invalid_option_title",
          descriptionKey: "general.errors.invalid_option_description",
          color: ColorCode.ERROR,
        });
        return;
      }
      targetTomoriId = selectedPersona.tomori_id;
      targetIsAlter = selectedPersona.is_alter === true;

      let remindersQuery = sql<ReminderSelectionRow[]>`
				SELECT
					r.reminder_id,
					r.reminder_purpose,
					r.reminder_time,
					r.repetition_interval_hours,
					r.channel_disc_id,
					r.created_by_user_id,
					r.user_discord_id,
					r.user_nickname,
					u.user_nickname AS created_by_nickname
				FROM reminders r
				LEFT JOIN users u
					ON r.created_by_user_id = u.user_id
				WHERE r.server_id = ${tomoriState.server_id}
			`;

      remindersQuery = targetIsAlter
        ? sql`${remindersQuery} AND r.persona_id = ${targetTomoriId}`
        : sql`${remindersQuery} AND (r.persona_id = ${targetTomoriId} OR r.persona_id IS NULL)`;

      if (!hasManagePermission) {
        remindersQuery = sql`${remindersQuery} AND r.created_by_user_id = ${userData.user_id}`;
      }

      remindersQuery = sql`${remindersQuery} ORDER BY r.reminder_time ASC`;
      const reminders = await remindersQuery;
      const selectionInteraction = personaSelectionInteraction ?? interaction;

      if (!reminders || reminders.length === 0) {
        await replyInfoEmbed(selectionInteraction, locale, {
          titleKey: "commands.forget.reminder.no_reminders_title",
          descriptionKey: "commands.forget.reminder.no_reminders",
          color: ColorCode.WARN,
        });
        return;
      }

      const timezoneOffset = tomoriState.config.timezone_offset ?? 0;
      const reminderSelectOptions: SelectOption[] = reminders.map(
        (reminder: ReminderSelectionRow, index: number) => {
          const formattedTime = formatTimeWithOffset(
            new Date(reminder.reminder_time),
            timezoneOffset,
            {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            },
          );

          const channelName =
            interaction.guild?.channels.cache.get(reminder.channel_disc_id)
              ?.name ?? reminder.channel_disc_id;
          const repeatText =
            typeof reminder.repetition_interval_hours === "number" &&
            reminder.repetition_interval_hours >= 1
              ? ` | repeats every ${reminder.repetition_interval_hours}h`
              : "";
          // For Matrix-originated reminders (created_by_user_id = null, user_discord_id
          // is a Matrix ID like "@bred:localhost"), show who the reminder is for so
          // server managers can identify and clean up "orphan" reminders.
          const isMatrixReminder =
            reminder.created_by_user_id === null &&
            isBridgeUserId(reminder.user_discord_id);
          const creatorName = isMatrixReminder
            ? `${reminder.user_nickname} (Matrix)`
            : (reminder.created_by_nickname ??
              (reminder.created_by_user_id
                ? `user #${reminder.created_by_user_id}`
                : "unknown"));
          const managerCreatedByText =
            hasManagePermission &&
            reminder.created_by_user_id !== userData.user_id
              ? isMatrixReminder
                ? ` | for ${creatorName}`
                : ` | created by ${creatorName}`
              : "";
          const description = `At ${formattedTime} (${formatUTCOffset(timezoneOffset)}) in #${channelName}${repeatText}${managerCreatedByText}`;

          return {
            label: safeSelectOptionText(reminder.reminder_purpose, 40),
            value: index.toString(),
            description: safeSelectOptionText(description),
          };
        },
      );

      const modalResult = await promptWithPaginatedModal(
        selectionInteraction,
        locale,
        {
          modalCustomId: MODAL_CUSTOM_ID,
          modalTitleKey: "commands.forget.reminder.modal_title",
          components: [
            {
              customId: REMINDER_SELECT_ID,
              labelKey: "commands.forget.reminder.select_label",
              descriptionKey: "commands.forget.reminder.select_description",
              placeholder: "commands.forget.reminder.select_placeholder",
              required: true,
              options: reminderSelectOptions,
            },
          ],
        },
      );

      // Handle modal outcome - loop back to persona picker on dismiss
      if (modalResult.outcome !== "submit") {
        log.info(
          `Reminder deletion modal ${modalResult.outcome} for user ${userData.user_id}`,
        );
        continue;
      }

      const modalSubmitInteraction = modalResult.interaction;
      const selectedIndex = modalResult.values?.[REMINDER_SELECT_ID];

      if (!modalSubmitInteraction || !selectedIndex) {
        log.error("Modal result unexpectedly missing interaction or values");
        return;
      }

      const selectedReminder = reminders[Number.parseInt(selectedIndex, 10)];
      if (!selectedReminder) {
        await replyInfoEmbed(modalSubmitInteraction, locale, {
          titleKey: "general.errors.operation_failed_title",
          descriptionKey: "general.errors.operation_failed_description",
          color: ColorCode.ERROR,
        });
        return;
      }

      await performReminderRemoval(
        selectedReminder,
        modalSubmitInteraction,
        locale,
      );
      break;
    }
  } catch (error) {
    const context: ErrorContext = {
      userId: userData.user_id,
      serverId: tomoriState?.server_id,
      tomoriId: targetTomoriId ?? tomoriState?.tomori_id,
      errorType: "CommandExecutionError",
      metadata: {
        command: "forget reminder",
        guildId: interaction.guild?.id,
        executorDiscordId: interaction.user.id,
      },
    };
    await log.error(
      `Unexpected error in /forget reminder for user ${userData.user_disc_id}`,
      error as Error,
      context,
    );

    const errorReplyTarget =
      personaSelectionInteraction &&
      !personaSelectionInteraction.deferred &&
      !personaSelectionInteraction.replied
        ? personaSelectionInteraction
        : interaction;
    await replyInfoEmbed(errorReplyTarget, locale, {
      titleKey: "general.errors.unknown_error_title",
      descriptionKey: "general.errors.unknown_error_description",
      color: ColorCode.ERROR,
      flags: MessageFlags.Ephemeral,
    });
  }
}
