import { createRewardCommand } from "./rewardHelper";

/** Headpat reward — give the bot a headpat and trigger a response */
export const { configureSubcommand, execute } = createRewardCommand("headpat");
