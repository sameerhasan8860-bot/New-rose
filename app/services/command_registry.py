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
    ("ban", "Ban a replied-to member"), ("unban", "Unban a replied-to member"),
    ("kick", "Remove a replied-to member"), ("mute", "Temporarily restrict a replied-to member"),
    ("unmute", "Restore send permissions"), ("warn", "Record a warning"),
    ("warnings", "Show warnings for a replied-to member"),
))
_REPORTING = (
    CommandSpec("report", "Report a replied-to message", AccessLevel.EVERYONE, True),
    CommandSpec("reports", "Review open group reports", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("adminlog", "View recent group moderation actions", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("save", "Save a replied-to message as a group note", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("get", "Retrieve a group note", AccessLevel.EVERYONE, True),
    CommandSpec("notes", "List saved group notes", AccessLevel.EVERYONE, True),
    CommandSpec("filter", "Create or update a keyword response", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("stop", "Remove a keyword filter", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("filters", "List group keyword filters", AccessLevel.EVERYONE, True),
    CommandSpec("welcome", "Enable or disable welcome messages", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("setwelcome", "Set the welcome message template", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("purge", "Delete up to 100 messages from a replied-to message onward", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("lock", "Lock a message category", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("unlock", "Unlock a message category", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("locks", "List active group locks", AccessLevel.EVERYONE, True),
    CommandSpec("blocklist", "Manage group blocked terms", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("goodbye", "Enable or disable leave messages", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("antiflood", "Enable or disable text flood protection", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("closereport", "Close a report in this group", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("resetwarnings", "Clear warnings for a replied-to member", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("captcha", "Enable or disable new-member CAPTCHA", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("antiraid", "Enable or disable join-spike alerts", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("topic", "Create, close, reopen, or delete forum topics", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("export", "Export allowlisted settings for this group", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("import", "Import a validated group settings export", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("fed", "Create, join, leave, or inspect an explicitly consented federation", AccessLevel.GROUP_ADMIN, True),
    CommandSpec("privacy", "View or erase your records in this group", AccessLevel.EVERYONE, True),
)
COMMANDS = _CORE + _MODERATION + _REPORTING
COMMAND_MAP = {item.name: item for item in COMMANDS}


def get_command(name: str) -> CommandSpec | None:
    return COMMAND_MAP.get(name.lstrip("/").split()[0].lower()) if name.strip() else None
