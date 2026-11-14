from app.handlers import BRAND
from app.services.command_registry import COMMAND_MAP, get_command


def test_brand_is_present():
    assert "𝗠𝗔𝗦𝗧𝗘𝗥" in BRAND
    assert "𝗫" in BRAND


def test_registry_includes_only_implemented_core_moderation_and_reporting_commands():
    expected = {"start", "help", "settings", "about", "id", "ping", "status",
                "ban", "unban", "kick", "mute", "unmute", "warn", "warnings",
                "report", "reports", "adminlog"}
    assert set(COMMAND_MAP) == expected
    assert get_command("/ban").implemented is True
    assert get_command("/report").implemented is True
    assert get_command("not-a-command") is None
