## DM Welcome Plain Text

### Goal
Make staff-configured DM welcome messages send as a normal DM message instead of an embed.

### Scope
- Keep the change isolated to the DM welcome branch in `discord_bot/cogs/social.py`.
- Do not change welcome-channel behavior.
- Do not change config storage or command surface.

### Approach
1. Add a regression test around `Social.on_member_join` proving DM welcome uses `member.send(dm_text)`.
2. Replace the embed-based DM send with a plain text send.
3. Re-run the targeted welcome/social tests.

### Risks
- Low risk. The only behavior change is message formatting in DMs.
