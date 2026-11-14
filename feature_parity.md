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
| Federation membership and basic ban propagation | IMPLEMENTED; automated tests for ledger | Create/join/leave/info plus /fban and /funban; only explicitly opted-in groups; checks bot Ban Users rights per destination; protects target admins; keeps ban ledger until every unban succeeds. No durable retry queue, federation roles, banlist/log/subscription management or private-group connections |
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


## Authoritative Rose command-reference coverage
The following official pages were inspected for command semantics. This is a bounded reference set, not an exhaustive extraction of every Rose module:

| Official reference | Verified command families | MASTER X implementation status |
|---|---|---|
| https://missrose.org/docs/basics/command-usage/ | on/off aliases; duration syntax | Partial: current toggles accept on/off; durations use s/m/h/d, not Rose's full documented syntax |
| https://missrose.org/docs/moderation/restrictions/ | ban, tban, dban, sban; mute, tmute, dmute, smute; kick, dkick, skick; unban, unmute | Partial: ban/unban/kick/mute/unmute plus /tban and /tmute exist; delete/silent variants and username target parsing are missing |
| https://missrose.org/docs/moderation/admins/ | admin permission mapping, promotion/demotion, anonymous admin verification | Partial: live group-admin verification exists; permission-specific command gates are inconsistent and anonymous admin verification is not implemented |
| https://missrose.org/docs/moderation/disabling/ | disabled, disableable, disable, enable, disableadmin, disabledel | Not implemented |
| https://missrose.org/docs/connections/ and https://missrose.org/docs/basics/connections/ | connect, disconnect, connection, reconnect; one active group and recent connection history | Not implemented |
| https://missrose.org/docs/federations/ and /docs/federations/creating/ | federation ownership, create/rename/delete, group opt-in | Partial: basic group-consented membership, plus basic /fban and /funban enforcement |
| https://missrose.org/docs/federations/fedbans/ and /docs/federations/managing/ | fban/unfban, fed admin roles, fed reasons/logs, banlist, subscriptions | Not implemented beyond schema groundwork; no cross-group ban enforcement |
| https://missrose.org/docs/advanced/bot-to-bot/ | off/admin/all modes and command review before bot admin actions | Not implemented; MASTER X fails closed and rejects bot-authored updates by default |

Do not advertise Rose command parity for any feature marked Partial or Not implemented. Rose-specific command behavior and permission requirements must be implemented and tested before changing these statuses.
