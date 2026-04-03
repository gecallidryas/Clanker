# Sanitized Root Promotion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Promote `femboibot-sanitized-with-holy-water` to become the effective project base at the repository root and remove the legacy duplicated root implementation.

**Architecture:** Replace the root project directories that currently duplicate the sanitized subtree with the sanitized versions, then strip generated and machine-local artifacts that do not belong in the canonical root. Preserve repository metadata such as `.git` and workspace tooling files that are not part of the duplicated runtime tree.

**Tech Stack:** PowerShell, git-tracked Python project files, repository file moves/copies

---

### Task 1: Snapshot the promotion target

**Files:**
- Inspect: `E:\femboibot\`
- Inspect: `E:\femboibot\femboibot-sanitized-with-holy-water\`

**Step 1: Record the target directories and files**

Confirm that `deploy`, `discord_bot`, `docs`, `tests`, `.gitignore`, and `README.md` are the sanitized root payload to promote.

**Step 2: Confirm preserved repo metadata**

Keep `.git` and `.agent` in place and avoid destructive operations outside `E:\femboibot`.

### Task 2: Promote the sanitized tree into the root

**Files:**
- Replace: `E:\femboibot\deploy\`
- Replace: `E:\femboibot\discord_bot\`
- Replace: `E:\femboibot\docs\`
- Replace: `E:\femboibot\tests\`
- Replace: `E:\femboibot\.gitignore`
- Create/Replace: `E:\femboibot\README.md`

**Step 1: Remove the legacy duplicated root directories/files**

Delete the root copies listed above before copying the sanitized versions into place.

**Step 2: Copy the sanitized versions into the root**

Copy the canonical directories and root files from `E:\femboibot\femboibot-sanitized-with-holy-water\`.

### Task 3: Clean generated artifacts and retire the staging subtree

**Files:**
- Clean: `E:\femboibot\discord_bot\`
- Remove: `E:\femboibot\femboibot-sanitized-with-holy-water\`

**Step 1: Remove generated and local artifacts from the promoted root**

Delete `__pycache__`, `.pytest_cache`, `.venv`, `.env`, `logs`, local database files, and copied custom/local avatar artifacts from the promoted project tree.

**Step 2: Remove the redundant sanitized subtree**

Delete `E:\femboibot\femboibot-sanitized-with-holy-water\` after the root promotion succeeds.

### Task 4: Verify the new base layout

**Files:**
- Inspect: `E:\femboibot\`

**Step 1: Verify root contents**

Confirm the root now contains the promoted sanitized project directories and no duplicate sanitized subtree.

**Step 2: Verify excluded artifacts are absent**

Check for remaining `.venv`, `.env`, `__pycache__`, `.pytest_cache`, log files, and local DB files under the promoted root tree.
