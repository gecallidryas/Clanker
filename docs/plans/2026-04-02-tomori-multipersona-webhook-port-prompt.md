# Execution Prompt: Tomori-Style Multi-Persona Webhook Port

Use this prompt in a fresh implementation session.

```text
You are implementing the plan in E:\femboibot\docs\plans\2026-04-02-tomori-multipersona-webhook-port.md.

Required workflow:
- Use superpowers:executing-plans.
- Use superpowers:test-driven-development for each behavior change.
- Use superpowers:verification-before-completion before claiming success.

Strict requirements:
- Match Tomori behavior exactly at the runtime semantics level:
  - one streamed response per persona invocation
  - a single persona/webhook identity per invocation
  - if multiple active personas are triggered, queue additional personas as separate follow-up jobs
  - later personas do not consume earlier persona replies as added context in the same invocation
- Do not duplicate infrastructure already present in this repo.
- Reuse the existing Python streaming stack:
  - E:\femboibot\discord_bot\utils\streaming\orchestrator.py
  - E:\femboibot\discord_bot\utils\streaming\discord_sender.py
  - E:\femboibot\discord_bot\utils\streaming\session_registry.py
- Reuse the existing provider entry points in E:\femboibot\discord_bot\utils\guild_ai.py.
- Do not port Tomori text chunkers, provider adapters, or unrelated queue systems into this repo.
- Remove or retire the current reply-sequence runtime in E:\femboibot\discord_bot\cogs\ai_brain.py instead of keeping two orchestration models alive.
- Add a startup/runtime guard so multiple local bot processes do not all answer the same Discord message.

Implementation expectations:
- Follow the plan task-by-task in order.
- Keep edits minimal and local to the files named in the plan.
- Before each production code change, write the failing test and run it.
- After each task, run the exact verification command from the plan.
- If the plan and code disagree, prefer the verified current repo structure and update the plan file before continuing.

Important repo-specific guidance:
- Active mode is currently single-value state in db_handler.py. Extend this carefully so single-persona behavior keeps working as the fallback/default path.
- Custom endpoint capability parsing already exists. Preserve it.
- The duplicate-reply bug caused by four local services is separate from persona logic. Fix it with runtime/process guarding, not reply heuristics.
- Webhook support should be introduced as an extension of the current sender path, not as a second sender stack.

Final output requirements:
- Summarize what changed.
- State exactly which existing modules were reused.
- State which old reply-sequence paths were removed or deprecated.
- Report the verification commands run and whether they passed.
```
