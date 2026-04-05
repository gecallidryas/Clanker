## Welcome Petpet Attachments

### Goal
Add a welcome-message upgrade so public welcome messages can mention the new member via `@user` and include a generated petting-avatar GIF attachment, with an optional per-guild toggle to include the same GIF in DM welcomes.

### Scope
- Keep the public welcome behavior inside the existing join flow in `discord_bot/cogs/social.py`.
- Preserve the current custom template placeholders and add `@user` as an alias for the new member mention.
- Add one small guild-config flag for optional DM petpet attachments.
- Implement the GIF renderer locally with Pillow and bundled hand assets.
- Do not add arbitrary attachment upload management for admins.

### Approach
1. Extend template rendering so both `{member}` and literal `@user` render to `member.mention`.
2. Create a dedicated `discord_bot/utils/petpet.py` utility that accepts avatar bytes, normalizes the image, renders a short hand-petting animation, and returns GIF bytes.
3. Add bundled transparent hand overlay assets under a dedicated assets directory used by the renderer.
4. Update the member-join flow to fetch the joining member avatar once, generate the GIF, and attach it to the public welcome send.
5. Add a new boolean guild-config flag so DM welcomes can optionally include the same generated GIF.
6. Extend the welcome config panel to display and edit the new DM petpet toggle.
7. Cover the behavior with focused tests for template rendering, public welcome attachment sending, DM toggle behavior, and GIF generation output.

### Behavior Notes
- Public welcomes should always attempt to include the petpet GIF when a welcome channel send occurs.
- DM welcomes should only include the petpet GIF when both DM welcomes and the new DM petpet toggle are enabled.
- If avatar fetch or GIF generation fails, the bot should still send the text welcome instead of dropping the message entirely.
- Allowed mentions for public welcomes must stay limited to user mentions only.

### Risks
- Pillow animation output can be fragile if frame sizes, disposal behavior, or palette handling are wrong, so the renderer should stay simple and deterministic.
- Discord asset fetching in `on_member_join` can fail or add latency; the code should fetch once and degrade to text-only sends on failure.
- Config panel and DB helper changes must stay backward-compatible for guilds that do not yet have the new flag stored.
