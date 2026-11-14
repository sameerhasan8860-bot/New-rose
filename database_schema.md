# Database Schema Plan and Phase 2 Baseline

Production target: PostgreSQL. SQLite is acceptable for isolated development tests only. SQLAlchemy 2 async ORM is used; each task must create its own AsyncSession. Do not share one AsyncSession across concurrent tasks.

## Implemented baseline models
- groups: tenant root, keyed by Telegram chat_id.
- group_settings: composite primary key (chat_id, key); JSON-encoded values.
- group_admins: composite primary key (chat_id, user_id); cache only, never authoritative for privileged actions.
- processed_updates: update_id primary key for duplicate delivery suppression.
- moderation_actions: tenant-scoped audit entries.
- warnings: tenant-scoped user warnings.

## Planned feature tables
users, filters, notes, custom_commands, welcome_settings, goodbye_settings, locks, blocklists, allowlists, captcha_sessions, reports, scheduled_messages, automation_rules, analytics_events, user_xp, reputation, ai_settings, ai_conversations, ai_memory, audit_logs, owner_settings.

## Isolation rules
- Every tenant-owned record includes chat_id and repository methods require chat_id.
- Composite keys/indexes begin with chat_id where relevant.
- User memory is scoped by (chat_id, user_id), opt-in, expiring, and deletable.
- Global owner settings are a separate namespace.
- Never perform an unscoped query to retrieve tenant settings.

## Migration rules
- Alembic versioned migrations are required before production rollout; create_all is development bootstrap only.
- Additive migrations by default; back up before destructive changes.
- Never cascade-delete audit records by default.
- Enforce foreign keys and tenant-aware unique constraints.
