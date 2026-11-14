# Product Requirements — MASTER X

## Product
A multi-tenant Telegram group-management system with moderation, protection, engagement analytics, automation, an optional AI companion, and a web dashboard.

## Users and roles
- Global developer/owner: platform-wide configuration and operations.
- Group owner: configuration for groups they own or are authorized to administer.
- Group administrator: moderation/configuration within granted Telegram permissions.
- Member: public commands, reports, and configured AI conversations.

## Product principles
1. Tenant isolation by chat_id on every group-scoped query.
2. Telegram admin status and specific rights are revalidated at action time.
3. AI is advisory for high-impact moderation; serious actions require human confirmation.
4. No feature is advertised as implemented before handler + authorization + persistence + tests exist.
5. Original implementation and identity; do not copy third-party code, logos, or proprietary assets.

## MVP acceptance
- Bot starts with a configured token and reports health.
- /start, /help, /settings, /about, /id, /ping, /status work.
- Unknown commands return useful help.
- Bot handles Telegram API errors without leaking secrets.
- CI installs dependencies and runs tests.
- Worker workflow is manually triggered and bounded.

## Later acceptance
Each module must define command syntax, role requirements, DB schema, failure behavior, tests, and feature parity status before being marked implemented.
