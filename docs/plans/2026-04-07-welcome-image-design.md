# Welcome Image Controls Design

**Date:** 2026-04-07

**Goal:** Add a configurable welcome-image feature to `/welcome manage` so guild staff can enable or disable welcome images, choose between the existing pettinghand GIF and a new `catmunch` image template, and route the selected image to the welcome channel, a specific channel, or DMs.

## Summary

The current welcome flow has two separate behaviors:

- public text welcomes are configured through `/welcome manage`
- the pettinghand GIF is always attached to the public welcome message when generation succeeds

This feature turns image attachments into an explicit welcome-image system. The image behavior becomes independently configurable from the text welcome flow and from the existing DM welcome text toggle. The selected image template is rendered once per join event and routed according to the configured destination.

## User-Facing Behavior

### Welcome Panel

`/welcome manage` remains the only admin entrypoint.

The panel should show a new welcome-image summary with:

- whether welcome images are enabled
- the selected template: `pettinghand` or `catmunch`
- the selected destination: welcome channel, specific channel, or DM
- the configured image channel when destination is `specific_channel`

The panel should expose actions to:

- toggle welcome images on or off
- choose the welcome-image template
- choose the destination type
- choose the destination channel
- send a test image

### Join Flow

Text welcome behavior stays unchanged.

If welcome images are enabled:

- render the selected template once
- send it to the configured destination

Destination behavior:

- `welcome_channel`: send the image to the configured welcome channel
- `specific_channel`: send the image to the configured image channel
- `dm`: DM the image to the joining member

The image destination is independent from the existing DM welcome text toggle and DM welcome message content. A guild can send the image by DM even when DM text welcomes are disabled.

## Configuration Model

Add four guild config fields:

- `welcome_image_enabled`
- `welcome_image_template`
- `welcome_image_destination`
- `welcome_image_channel_id`

Default values for existing guilds:

- `welcome_image_enabled = 0`
- `welcome_image_template = "pettinghand"`
- `welcome_image_destination = "welcome_channel"`
- `welcome_image_channel_id = NULL`

`get_welcome_config()` should return these values so the config panel and join logic use one shared config shape.

## Rendering Design

### Pettinghand

Keep the existing pettinghand renderer as the `pettinghand` template implementation.

### Catmunch

Add a new static PNG renderer that:

- loads `catmunch/cattomunch (2).png`
- loads `catmunch/ArtistsAlleyBB.otf`
- fetches the joining member's avatar as PNG
- crops and scales the avatar to fit inside the center circle
- composites the avatar underneath the cat art so the paws stay visible
- renders the requested text around the asset

Text content:

- above: member display name
- above: `joined the server`
- below: `snacknumber#{nth joiner}`

The nth joiner value should reuse the same ordinal formatting used by the existing welcome text flow.

## Error Handling

Welcome-image failures must not break the rest of the join flow.

Failure cases:

- avatar fetch failure
- missing configured destination channel
- missing DM permissions
- image renderer exceptions

Behavior on failure:

- log a warning
- skip the image send
- continue autorole, text welcome, and DM text welcome logic

## Testing Strategy

### Config and Panel

- update the config-panel surface test to lock in the new action values
- add tests for `get_welcome_config()` defaults and returned image settings

### Runtime

- add routing tests for welcome channel, specific channel, and DM destination handling
- add utility tests for:
  - pettinghand renderer returning GIF bytes
  - catmunch renderer returning PNG bytes

### Regression Expectations

- welcome text behavior remains unchanged when welcome images are disabled
- DM image sends do not depend on the DM welcome text toggle
- missing image destinations do not block the rest of the join workflow
