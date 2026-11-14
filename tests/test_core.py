from app.handlers import BRAND
from app.services.command_registry import COMMAND_MAP, get_command


def test_brand_is_present():
    assert "𝗠𝗔𝗦𝗧𝗘𝗥" in BRAND
    assert "𝗫" in BRAND


def test_registry_includes_only_implemented_core_moderation_and_reporting_commands():
    expected = {"start", "help", "settings", "about", "id", "ping", "status",
                "ban", "unban", "kick", "mute", "unmute", "warn", "warnings",
                "report", "reports", "adminlog", "save", "get", "notes", "filter", "stop", "filters", "welcome", "setwelcome", "purge", "lock", "unlock", "locks", "blocklist", "goodbye", "antiflood", "closereport", "resetwarnings"}
    assert set(COMMAND_MAP) == expected
    assert get_command("/ban").implemented is True
    assert get_command("/report").implemented is True
    assert get_command("/save").implemented is True
    assert get_command("not-a-command") is None


def test_duration_parser_bounds():
    from app.handlers import _parse_duration
    assert _parse_duration("10m").total_seconds() == 600
    assert _parse_duration("2d").total_seconds() == 172800
    assert _parse_duration("0m") is None
    assert _parse_duration("999d") is None
    assert _parse_duration("10x") is None
