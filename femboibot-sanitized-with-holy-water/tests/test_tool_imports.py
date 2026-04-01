import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHONPATH = str(ROOT / "discord_bot")


def _run_import(module_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, r'{PYTHONPATH}'); "
                f"import {module_name}; "
                "print('ok')"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_import_utils_tool_registry_cleanly():
    result = _run_import("utils.tool_registry")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_import_cogs_ai_brain_cleanly():
    result = _run_import("cogs.ai_brain")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
