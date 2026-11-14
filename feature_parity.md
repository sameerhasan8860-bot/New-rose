# Feature Parity Tracker

Status definitions:
- NOT STARTED: no implementation work.
- IN PROGRESS: actively being developed.
- IMPLEMENTED: handler/service and persistence exist.
- TESTED: automated or integration tests passed.
- VERIFIED: real Telegram behavior verified and evidence recorded.

## Rose — source of truth
Official documentation sidebar covers Basics (command usage, info, connections, languages, rules), Moderation (admins, pins, approvals, purges, logs, restrictions, warnings, reports, command disabling), Greetings, Anti-spam (locks, CAPTCHA, blocklists, antiflood, antiraid), Federations, Filters, Notes, Formatting, Connections, Echo, import/export, Privacy, Topics, Cleaning, Advanced and Bot-to-Bot.
Source: https://missrose.org/docs/
Full command extraction remains IN PROGRESS; do not claim full Rose parity from this partial catalogue.

| Feature family | MASTER X status | Notes |
|---|---|---|
| Moderation, reports, notes, filters, greetings, locks, blocklist | IMPLEMENTED; automated coverage partial | See command_catalog.md |
| CAPTCHA, antiraid alerts, forum topics | IMPLEMENTED; live Telegram verification pending | Antiraid join windows and alert claims are persisted across workers; CAPTCHA stores/restores member permissions when available; CI #192 passed |
| Import/export | IMPLEMENTED; CI test pending | Versioned JSON; allowlisted group settings only |
| Federation membership | IMPLEMENTED; tests added | Create/join/leave/info with per-group admin consent; no cross-group enforcement/ban propagation yet |
| Privacy | IMPLEMENTED; tests added | Self-service erasure of this user's records in the current group only; Telegram messages and other groups unaffected |
| Cleaning/formatting | IMPLEMENTED; formatting tests added | /clean bounded to 20 messages and permission-gated; /format escapes HTML |
| Bot-to-bot safeguards | BASELINE PROTECTION TESTED; advanced parity PARTIAL | Router rejects bot-authored messages and callbacks by default; anonymous sender identities fail closed. No admin/all mode or approval-review workflow; this is intentionally safer than enabling bot commands without review |

## Group Help — publicly documented capabilities
Verified public feature page lists join protection/CAPTCHA, anti-spam, anti-flood, anti-porn, banned words, night mode, and a free clone bot with custom name/profile image. Pricing page additionally lists moderation commands, welcome/goodbye/rules, custom commands, message deletion, automatic replies, mention notifications, and recurring messages at plan-dependent levels.
Sources: https://grouphelp.me/en and https://grouphelp.me/en/pricing
Do not infer undocumented command syntax.

## Iris
The official Iris project site (iris-tg.ru) identifies these feature families: moderation commands, moderator topics, warnings, user profiles/questionnaires, chat statistics, reputation, bookmarks, catalogue, rewards, map, virtual economy, and group-representative/userbot integrations. The official support/help channel @irissup also documents anti-scam/spammer/new-account notifications, configurable filters, and trigger rules. Exact command syntax and access conditions must be extracted from the official command reference before implementation; some Iris features are ecosystem-specific and may not map to Telegram Bot API.
Sources: https://iris-tg.ru/ ; https://t.me/irissup

## Combot
Official product page verifies analytics, moderation/filtering, spam/flood protection, scheduled announcements, trigger system, reputation, and CAS anti-spam. Current official site content may evolve; paid/free availability and API access must be checked before designing dependencies.
Source: https://combot.org/

## Telegram platform constraints
Privacy mode limits which group messages a bot receives. Admin bots receive all group messages; a bot can also be configured through BotFather to disable privacy mode, which requires re-adding it for the change to apply. Command scopes do not replace backend authorization.
Source: https://core.telegram.org/bots/features
