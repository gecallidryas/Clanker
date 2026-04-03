import { createRewardCommand } from "./rewardHelper";

/** Kiss reward — give the bot a kiss and trigger a response */
export const { configureSubcommand, execute } = createRewardCommand("kiss");
