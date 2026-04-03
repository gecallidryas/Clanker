import asyncio
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "discord_bot"))

if "utils.rag_store" not in sys.modules:
    rag_store_stub = types.ModuleType("utils.rag_store")

    async def _dummy_get_rag_context(*args, **kwargs):
        return ""

    rag_store_stub.get_rag_context = _dummy_get_rag_context
    sys.modules["utils.rag_store"] = rag_store_stub

from cogs import ai_brain as ai_brain_mod  # noqa: E402
from utils.persona_queue import PersonaInvocationJob, PersonaQueueManager  # noqa: E402


class _FakeBot:
    def __init__(self):
        self.user = types.SimpleNamespace(id=999, display_name="Femmy")


class AIBrainPersonaQueueTests(unittest.TestCase):
    def setUp(self):
        self._orig_register_builtin_tools = ai_brain_mod.register_builtin_tools
        ai_brain_mod.register_builtin_tools = lambda: None
        self.brain = ai_brain_mod.AIBrain(_FakeBot())

    def tearDown(self):
        ai_brain_mod.register_builtin_tools = self._orig_register_builtin_tools

    def test_multi_persona_trigger_enqueues_followup_persona_jobs(self):
        jobs = self.brain._build_persona_jobs(
            primary_mode_key="mode_femboy",
            active_mode_keys=["mode_femboy", "mode_oneesan"],
            triggered_mode_keys=["mode_oneesan", "mode_femboy"],
            multi_persona_enabled=True,
            triggered_persona_limit=2,
        )

        self.assertEqual([job.mode_key for job in jobs], ["mode_oneesan", "mode_femboy"])

    def test_multi_persona_disabled_falls_back_to_primary_mode(self):
        jobs = self.brain._build_persona_jobs(
            primary_mode_key="mode_femboy",
            active_mode_keys=["mode_femboy", "mode_oneesan"],
            triggered_mode_keys=["mode_oneesan", "mode_femboy"],
            multi_persona_enabled=False,
            triggered_persona_limit=2,
        )

        self.assertEqual([job.mode_key for job in jobs], ["mode_femboy"])

    def test_triggered_persona_limit_caps_followup_jobs(self):
        jobs = self.brain._build_persona_jobs(
            primary_mode_key="mode_femboy",
            active_mode_keys=["mode_femboy", "mode_oneesan", "mode_tsundere"],
            triggered_mode_keys=["mode_oneesan", "mode_femboy", "mode_tsundere"],
            multi_persona_enabled=True,
            triggered_persona_limit=2,
        )

        self.assertEqual([job.mode_key for job in jobs], ["mode_oneesan", "mode_femboy"])


class PersonaQueueManagerTests(unittest.TestCase):
    def test_queue_manager_runs_jobs_sequentially_per_channel(self):
        async def _run():
            manager = PersonaQueueManager()
            seen = []

            await manager.enqueue(55, PersonaInvocationJob(mode_key="mode_oneesan"))
            await manager.enqueue(55, PersonaInvocationJob(mode_key="mode_femboy"))

            async def runner(job):
                seen.append(job.mode_key)

            await manager.drain(55, runner)

            self.assertEqual(seen, ["mode_oneesan", "mode_femboy"])

        asyncio.run(_run())
