from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_teach_memory_commands_removed():
    source = _read("discord_bot/cogs/teach.py")
    assert "memory_group = app_commands.Group" not in source
    assert '@memory_group.command(name="personal"' not in source
    assert '@memory_group.command(name="server"' not in source


def test_remember_group_has_personal_and_server_subcommands():
    source = _read("discord_bot/cogs/memories.py")
    assert 'remember_group = app_commands.Group(name="remember"' in source
    assert '@remember_group.command(name="personal"' in source
    assert '@remember_group.command(name="server"' in source


def test_remember_no_500_char_limit_checks():
    source = _read("discord_bot/cogs/memories.py")
    assert "Fact too long! Please keep it under 500 characters." not in source
    assert "len(fact) > 500" not in source


def test_tools_refresh_command_exists():
    source = _read("discord_bot/cogs/tools_admin.py")
    assert '@tools_group.command(\n        name="refresh"' in source


def test_tools_clear_guild_recency_command_exists():
    source = _read("discord_bot/cogs/tools_admin.py")
    assert 'name="clear-guild-recency"' in source


def test_slash_forget_no_long_term_choice():
    source = _read("discord_bot/cogs/memories.py")
    assert 'app_commands.Choice(name="long_term", value="long_term")' not in source
