from dataclasses import dataclass
from enum import StrEnum


class AccessLevel(StrEnum):
    EVERYONE = "everyone"
    GROUP_ADMIN = "group_admin"
    GLOBAL_OWNER = "global_owner"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    name: str
    description: str
    access: AccessLevel = AccessLevel.EVERYONE
    group_only: bool = False
    implemented: bool = True


_CORE = (
    CommandSpec("start", "Welcome to MASTER X"),
    CommandSpec("help", "Show available commands"),
    CommandSpec("settings", "Show group settings status", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("about", "About MASTER X"),
    CommandSpec("id", "Show chat and user IDs"),
    CommandSpec("ping", "Check bot response"),
    CommandSpec("status", "Show basic runtime status"),
)
_MODERATION = tuple(CommandSpec(name, description, AccessLevel.GROUP_ADMIN, True) for name, description in (
    ("ban", "Ban a replied-to member"),
    ("unban", "Unban a replied-to member"),
    ("kick", "Remove a replied-to member"),
    ("mute", "Temporarily restrict a replied-to member"),
    ("unmute", "Restore send permissions"),
    ("warn", "Record a warning for a replied-to member"),
    ("warnings", "Show warnings for a replied-to member"),
))
COMMANDS = _CORE + _MODERATION
COMMAND_MAP = {item.name: item for item in COMMANDS}


def get_command(name: str) -> CommandSpec | None:
    return COMMAND_MAP.get(name.lstrip("/").split()[0].lower()) if name.strip() else None
