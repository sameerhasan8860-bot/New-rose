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
Initial status: NOT STARTED. Full command extraction remains a task; examples in the product brief are not the full catalogue.

## Group Help — publicly documented capabilities
Verified public feature page lists join protection/CAPTCHA, anti-spam, anti-flood, anti-porn, banned words, night mode, and a free clone bot with custom name/profile image. Pricing page additionally lists moderation commands, welcome/goodbye/rules, custom commands, message deletion, automatic replies, mention notifications, and recurring messages at plan-dependent levels.
Sources: https://grouphelp.me/en and https://grouphelp.me/en/pricing
Initial status: NOT STARTED. Do not infer undocumented command syntax.

## Iris
The official Iris project site (iris-tg.ru) identifies these feature families: moderation commands, moderator topics, warnings, user profiles/questionnaires, chat statistics, reputation, bookmarks, catalogue, rewards, map, virtual economy, and group-representative/userbot integrations. The official support/help channel @irissup also documents anti-scam/spammer/new-account notifications, configurable filters, and trigger rules. Exact command syntax and access conditions must be extracted from the official command reference before implementation; some Iris features are ecosystem-specific and may not map to Telegram Bot API.
Sources: https://iris-tg.ru/ ; https://t.me/irissup
Initial status: RESEARCH IN PROGRESS. Feature families are verified at a high level; command-level parity is not yet verified.

## Combot
Official product page verifies analytics, moderation/filtering, spam/flood protection, scheduled announcements, trigger system, reputation, and CAS anti-spam. Current official site content may evolve; paid/free availability and API access must be checked before designing dependencies.
Source: https://combot.org/
Initial status: NOT STARTED.

## Telegram platform constraints
Privacy mode limits which group messages a bot receives. Admin bots receive all group messages; a bot can also be configured through BotFather to disable privacy mode, which requires re-adding it for the change to apply. Command scopes do not replace backend authorization.
Source: https://core.telegram.org/bots/features
