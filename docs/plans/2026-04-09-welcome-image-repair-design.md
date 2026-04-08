# Welcome Image Repair Design

**Problem**

Older guild databases can exist without the `welcome_image_*` columns, which makes the welcome image toggle unreliable for those servers. The current welcome-image routing is also more complex than needed because it supports a separate image destination and image channel even though the desired behavior is to send the image alongside the normal welcome text in the main welcome channel.

**Approved Direction**

Repair guild schemas in place so every guild database reliably contains the welcome-image columns. Simplify runtime behavior so welcome images always follow the main welcome channel for server welcomes, using the same configured channel as the text welcome.

**Approach Options**

1. In-place schema repair plus simplified routing.
Recommended because it preserves guild data, fixes the toggle for old guild DBs, and removes the confusing extra routing path.

2. Reset affected guild DBs.
Rejected because it would wipe per-guild settings and stored state, and still would not simplify the confusing config surface.

3. Keep the current routing and only patch the toggle.
Rejected because it would leave the UX confusing and preserve dead complexity around separate image routing.

**Design**

- Add a dedicated guild-config schema repair helper in `discord_bot/utils/db_handler.py` that ensures missing `welcome_image_enabled`, `welcome_image_template`, `welcome_image_destination`, and `welcome_image_channel_id` columns are added for legacy guild DBs.
- Call that repair during normal guild schema initialization so existing guild DBs are healed automatically.
- Simplify welcome image delivery in `discord_bot/cogs/social.py` and `discord_bot/cogs/config.py` so previews and real sends use the main welcome channel instead of the separate image destination/image channel path.
- Keep legacy columns in the schema for compatibility, but stop depending on them for runtime routing.
- Update tests to cover legacy schema repair and main-channel-only welcome image behavior.

**Error Handling**

- If the main welcome channel is not configured, enabling welcome images should be blocked in the same way normal welcome messages are blocked.
- Schema repair should be deterministic and idempotent.
- Missing render assets should still surface as preview/send failures without corrupting config state.

**Testing**

- Add a regression test that reproduces a legacy guild DB missing welcome-image columns and verifies schema repair adds them.
- Add toggle tests that verify enabling/disabling welcome images works after repair.
- Update welcome-image routing tests so runtime and preview sends use the main welcome channel.
