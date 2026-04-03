import { createRewardCommand } from "./rewardHelper";

/** Tickle reward — tickle the bot and trigger a response */
export const { configureSubcommand, execute } = createRewardCommand("tickle");
