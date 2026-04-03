import { createRewardCommand } from "./rewardHelper";

/** Hug reward — give the bot a hug and trigger a response */
export const { configureSubcommand, execute } = createRewardCommand("hug");
