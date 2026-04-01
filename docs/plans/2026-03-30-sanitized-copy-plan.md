# Sanitized Copy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a clean subfolder inside the repo that contains the femboibot runtime code plus tests and deployment files, without `tomoribot_reference` content or local machine artifacts.

**Architecture:** Build a conservative project copy under `E:\femboibot\femboibot-sanitized-with-holy-water` by copying the active bot package, test suite, deployment files, and minimal root-level metadata. Exclude caches, logs, virtual environments, local env files, and unrelated reference or analysis material.

**Tech Stack:** PowerShell, Python project structure, git-tracked repository files

---

### Task 1: Create the sanitized project layout

**Files:**
- Create: `E:\femboibot\femboibot-sanitized-with-holy-water\`
- Copy: `E:\femboibot\discord_bot\`
- Copy: `E:\femboibot\tests\`
- Copy: `E:\femboibot\deploy\`
- Copy: `E:\femboibot\.gitignore`

**Step 1: Remove any stale sanitized folder before copying**

Run: `Remove-Item -Recurse -Force E:\femboibot\femboibot-sanitized-with-holy-water`
Expected: folder removed if it already exists

**Step 2: Create the destination root**

Run: `New-Item -ItemType Directory -Path E:\femboibot\femboibot-sanitized-with-holy-water`
Expected: destination folder exists

**Step 3: Copy the selected project directories**

Run: copy `discord_bot`, `tests`, and `deploy` into the destination
Expected: sanitized folder contains runnable bot code, tests, and deployment assets

**Step 4: Remove excluded artifacts from copied directories**

Run: delete copied `__pycache__`, `.pytest_cache`, `logs`, local `.env`, and other transient files
Expected: no machine-specific or generated runtime clutter remains

### Task 2: Add minimal sanitized-root metadata

**Files:**
- Create: `E:\femboibot\femboibot-sanitized-with-holy-water\README.md`

**Step 1: Write a brief README**

Include:
- what the folder contains
- what was intentionally excluded
- how to install dependencies and run the bot from `discord_bot`
- how to run tests

Expected: the new folder is understandable without needing the parent repo

### Task 3: Verify the sanitized copy

**Files:**
- Inspect: `E:\femboibot\femboibot-sanitized-with-holy-water\**`

**Step 1: List the copied files**

Run: recursive file listing under the sanitized folder
Expected: only the intended directories and files are present

**Step 2: Search for excluded references**

Run: search for `tomoribot_reference`
Expected: no matches

**Step 3: Search for copied local artifact directories or files**

Run: search for `__pycache__`, `.pytest_cache`, `.venv`, `.env`, and `logs`
Expected: excluded artifacts are absent except for sample env files such as `.env.example`
