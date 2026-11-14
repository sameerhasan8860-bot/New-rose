# MongoDB Migration Plan

## Goal

Move MASTER X completely from SQLAlchemy/Alembic and relational databases to MongoDB. The target runtime must not require SQLite, PostgreSQL, SQLAlchemy, Alembic, a relational connection URL, or relational migrations.

## Target stack

- PyMongo Async API (`pymongo[async]`) with MongoDB's native async client.
- One MongoDB database selected by `MONGODB_URI` and optional `MONGODB_DATABASE`.
- Explicit collection/repository layer under `app/db/`.
- MongoDB indexes created idempotently at startup.
- UTC-aware BSON datetimes and Telegram chat/user IDs stored as 64-bit integers.
- Every group-owned document carries `chat_id`; repository methods must scope reads and writes by it.

## Collections

- `groups`
- `group_settings`
- `group_admins`
- `processed_updates`
- `update_claims`
- `moderation_actions`
- `warnings`
- `reports`
- `notes`
- `group_filters`
- `blocked_terms`
- `captcha_challenges`
- `federations`
- `federation_groups`
- `federation_bans`
- `raid_join_events`
- `raid_alerts`

Use MongoDB unique compound indexes to preserve current uniqueness guarantees, including group-scoped setting keys, note names, filter triggers, federation membership, federation bans, update IDs, update leases, and raid alert deduplication.

## Migration sequence

1. Replace database configuration, engine lifecycle, and startup wiring with an async MongoDB client; validate the URI before bot startup.
2. Implement typed collection repositories and atomic update-claim/deduplication operations using MongoDB unique indexes and conditional updates.
3. Port each service and handler query from SQLAlchemy sessions/models to repository operations. Preserve transaction boundaries where possible; use MongoDB transactions only where deployment topology supports them, and design idempotent workflows for standalone clusters.
4. Port privacy deletion, CAPTCHA claim/restore, antiraid deduplication, federation membership/ban operations, and command settings with group-tenant isolation.
5. Rewrite tests to run against a real MongoDB service in CI, including unique-index races, lease expiry, cross-group isolation, and startup validation.
6. Remove Alembic, migrations, SQLAlchemy, aiosqlite, asyncpg, relational test jobs, and all SQL-only code only after no runtime/test imports remain.
7. Update deployment secrets and documentation to require `BOT_TOKEN` and `MONGODB_URI`; never log credentials.

## Safety and compatibility

- Do not silently drop or overwrite existing database data.
- This is a backend replacement, not an in-place SQLite/PostgreSQL data conversion. If existing relational data must be retained, build and verify a separate export/import utility before switching production.
- Keep the existing `main` branch untouched until MongoDB implementation, CI, and a user-approved Telegram test-group smoke test pass.
- Never request or commit the actual MongoDB URI. Configure it only as a GitHub Actions secret named `MONGODB_URI`.
- Do not mark the migration complete while any SQLAlchemy/Alembic dependency, import, migration step, or relational CI service remains.
