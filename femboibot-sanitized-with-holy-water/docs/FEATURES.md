# Femmy Bot Features

## Primary Admin Surfaces

- `/config panel`
  Use this as the main server-configuration surface. It is intended to replace most granular config subcommands with Discord-native panels for capabilities, AI behavior, providers/models, welcome flows, routing, and moderation settings.
- `/tools manage`
  Use this for bulk tool-capability management. `/tools refresh` remains separate because it is an operational action, not persisted configuration.
- `/persona manage`
  Use this for active mode switching, evil-mode switching, persona previewing, and built-in/custom persona management from one admin surface.

## Configuration Areas

- Capabilities and tools
  Bulk-enable or bulk-disable grouped tool/config flags instead of toggling one setting at a time.
- AI reply settings
  Manage cooldowns, thresholds, self-reply limits, streaming behavior, thought/debug logging, AI whitelists, and AI auto-channel routing.
- Providers and models
  Review masked secret state, current model routing, and custom endpoint settings from one section.
- Welcome and autorole
  Configure welcome channels/messages, DM welcome messaging, and autorole behavior from the same panel architecture.
- Staff and modlog
  Manage staff-role access and moderation-log routing as high-risk admin actions.

## Persona and Presentation

- Built-in and custom personas are managed together.
- Active mode selection and evil-mode switching are part of the same workflow.
- Custom personas support create, edit, preview, duplicate, and delete flows.
- Deleting the active custom persona should safely fall back to the default mode.

## Security and Audit

- High-risk actions use risk-based config auth rather than requiring auth for every change.
- Secrets, destructive actions, staff-role edits, and modlog edits are treated as authenticated actions.
- Guild config audit entries use normalized categories with structured detail support for richer admin and audit trails.

## Transitional Commands

- Old granular commands may still exist temporarily as migration shims.
- When a shim remains, it should perform the action and point admins toward `/config panel`, `/tools manage`, or `/persona manage`.
