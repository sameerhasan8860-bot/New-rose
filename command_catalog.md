# Command Catalogue

Only Phase 1 commands below are implemented in the starter. All other commands are planned, not registered, and must not be advertised as working.

| Command | Scope | Phase 1 behavior | Status |
|---|---|---|---|
| /start | Private/group | Branded introduction | IN PROGRESS |
| /help | All | Lists currently available core commands | IN PROGRESS |
| /settings | Private/group | Explains that group settings UI is upcoming | IN PROGRESS |
| /about | All | Product identity and current stage | IN PROGRESS |
| /id | All | Returns current chat and actor IDs | IN PROGRESS |
| /ping | All | Basic process response | IN PROGRESS |
| /status | All | Runtime status without secrets | IN PROGRESS |

Planned categories: ADMIN, MODERATION, ANTISPAM, WELCOME, FILTERS, NOTES, LOCKS, CAPTCHA, AUTOMATION, ANALYTICS, AI, XP, OWNER.

Command contract for every future entry: canonical syntax, aliases, argument parser, target resolution (reply/ID/username), role requirement, required Telegram rights, persistence, success/error response, tests, and help text.

Do not register a command in Telegram's command menu until its handler is available. Telegram command menus are discoverability only; authorization is always checked server-side.
