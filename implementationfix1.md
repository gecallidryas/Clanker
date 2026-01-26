# Implementation Plan: Keyword Triggers, Media Analysis & Sync Command Fixes

## Problem Summary

1. **Keyword triggers not working** - Bot doesn't respond when users say "femmy", "yumi", etc.
2. **Media analysis may reply before complete** - Need to ensure full analysis before responding
3. **`!sync` command needs confirmation message** - Currently syncs but doesn't confirm

---

## Root Cause Analysis

### Issue 1: Keyword Triggers Bug (CRITICAL)

**Location:** `cogs/ai_brain.py` lines 883-888

**The Bug:**
```python
if not should_respond:
    if not any(trigger in content_lower for trigger in ALL_TRIGGERS):
        return
    return  # <-- BUG: Always returns, even when trigger is found!
```

Both paths lead to `return`, so even if a trigger word is detected, the bot never responds.

### Issue 2: Missing Trigger Words

**Current triggers for `mode_oneesan`:** `["yumi", "yumi chan", "yumi-chan", "oneesan", "onesan"]`
**Missing:** `"yumi-san"` (user requested)

### Issue 3: Sync Command Confirmation

The `!sync` command exists but may not be sending the confirmation message due to an exception.

---

## Implementation Stages

### Stage 1: Fix Keyword Trigger Logic
**Priority: HIGH**

#### TODO:
- [ ] Remove the redundant `return` statement in the trigger check block
- [ ] The logic should be: if no triggers at all, return early (performance). If has trigger, continue.
- [ ] Actually, the whole block is wrong - `should_respond` already checked `has_trigger`

**Fix:**
```python
# BEFORE (buggy)
if not should_respond:
    if not any(trigger in content_lower for trigger in ALL_TRIGGERS):
        return
    return  # <-- DELETE THIS LINE

# AFTER (fixed)
if not should_respond:
    return  # Simply return if we shouldn't respond
```

---

### Stage 2: Add Missing Trigger Words
**Priority: MEDIUM**

#### TODO:
- [ ] Add `"yumi-san"` to `MODE_TRIGGERS["mode_oneesan"]`

**Location:** `cogs/ai_brain.py` line 67

**Change:**
```python
# BEFORE
"mode_oneesan": ["yumi", "yumi chan", "yumi-chan", "oneesan", "onesan"],

# AFTER
"mode_oneesan": ["yumi", "yumi chan", "yumi-chan", "yumi-san", "oneesan", "onesan"],
```

---

### Stage 3: Ensure Complete Media Analysis Before Reply
**Priority: MEDIUM**

#### Current Flow:
1. `on_message` receives message with attachment
2. Calls `self._describe_images(message)` which uses `await` - already blocking
3. Builds prompt with image descriptions
4. Generates AI response

#### Analysis:
The current implementation ALREADY uses `await` on `_describe_images()`, which means it waits for completion. However, we should:

#### TODO:
- [ ] Add logging to confirm image analysis completion
- [ ] Add typing indicator BEFORE image analysis starts
- [ ] Ensure error handling doesn't skip analysis

**Enhancement:**
```python
async with message.channel.typing():
    if message.attachments:
        logger.info("Analyzing %d attachments...", len(message.attachments))
        image_descriptions = await self._describe_images(message)
        logger.info("Image analysis complete: %d descriptions", len(image_descriptions))
```

---

### Stage 4: Fix Sync Command Confirmation
**Priority: HIGH**

#### TODO:
- [ ] Add try/except block around sync logic
- [ ] Ensure confirmation message is sent
- [ ] Log sync attempts

**Location:** `main.py` lines 178-187

**Enhancement:**
```python
@commands.command(name='sync')
@commands.has_permissions(manage_guild=True)
async def sync_command(ctx: commands.Context):
    """Sync slash commands to this server."""
    try:
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        fmt = await ctx.bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Synced {len(fmt)} slash commands to **{ctx.guild.name}**!")
        logger.info("Synced %d commands to guild %s", len(fmt), ctx.guild.id)
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")
        logger.error("Sync failed: %s", e)
```

---

## File Changes Summary

| File | Changes |
|------|---------|
| `cogs/ai_brain.py` | Fix trigger logic bug, add "yumi-san" trigger, enhance media analysis logging |
| `main.py` | Add error handling and confirmation to sync command |

---

## Testing Plan

1. **Test keyword triggers:**
   - Say "femmy" in chat (bot in femboy mode) → should respond
   - Say "yumi-chan" in chat (bot in oneesan mode) → should respond
   - Say "yumi-san" in chat → should respond (new trigger)

2. **Test media analysis:**
   - Send an image with caption → bot should analyze image before responding
   - Check logs for "Image analysis complete" message

3. **Test sync command:**
   - Run `!sync` → should get confirmation message with count
   - Run with wrong permissions → should get error message

---

## Verification Commands

```bash
# After deploying, check logs for:
sudo journalctl -u femmy-bot -f | grep -i "trigger\|sync\|image analysis"
```
