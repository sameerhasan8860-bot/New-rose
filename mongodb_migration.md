# MongoDB Migration Plan

## Goal

Move MASTER X completely from SQLAlchemy/Alembic and relational databases to MongoDB. The target runtime must not require SQLite, PostgreSQL, SQLAlchemy, Alembic, a relational connection URL, or relational migrations.

## Target stack

- PyMongo Async API (`pymongo[srv]`) with MongoDB's native async client.
- One MongoDB database selected by `MONGODB_URI` and `MONGODB_DATABASE`.
- Explicit collection/repository layer under `app/db/`.
- MongoDB indexes created idempotently at startup.
- UTC-aware BSON datetimes and Telegram chat/user IDs stored as 64-bit integers.
- Every group-owned document carries `chat_id`; repository methods must scope reads and writes by it.

## Collections

`groups`, `group_settings`, `group_admins`, `processed_updates`, `update_claims`, `moderation_actions`, `warnings`, `reports`, `notes`, `group_filters`, `blocked_terms`, `captcha_challenges`, `federations`, `federation_groups`, `federation_bans`, `raid_join_events`, and `raid_alerts`.

Unique compound indexes preserve group-scoped setting keys, note names, filter triggers, federation membership, federation bans, update IDs, and raid-alert deduplication.

## Migration sequence

1. Add async MongoDB connection lifecycle and idempotent indexes.
2. Implement typed collection repositories and atomic update claims.
3. Port every service and handler query from SQLAlchemy sessions/models to repository operations.
4. Port privacy deletion, CAPTCHA claim/restore, antiraid deduplication, federation membership/ban operations, and command settings with group-tenant isolation.
5. Rewrite tests to run against MongoDB in CI, including unique-index races, lease expiry, cross-group isolation, and startup validation.
6. Remove Alembic, migrations, SQLAlchemy, aiosqlite, asyncpg, relational CI services, and SQL-only code only after no runtime/test imports remain.
7. Switch deployment secrets to `BOT_TOKEN` and `MONGODB_URI`; never log credentials.

## Current progress

- [x] Migration branch created; `main` remains unchanged.
- [x] Async MongoDB client lifecycle and ping check implemented as an isolated migration layer.
- [x] Idempotent collection index bootstrap implemented.
- [ ] Collection repositories and atomic operations.
- [ ] Port all service and handler persistence.
- [ ] MongoDB-backed CI and tests.
- [ ] Remove all relational dependencies and Alembic.
- [ ] User-approved Telegram test-group smoke test.

## Safety and compatibility

- Do not silently drop or overwrite existing database data.
- This backend replacement does not automatically convert existing SQLite/PostgreSQL data. If relational data must be retained, build and verify a separate export/import utility before switching production.
- Keep `main` untouched until MongoDB implementation, CI, and a user-approved Telegram test-group smoke test pass.
- Never request or commit the actual MongoDB URI. Configure it only as a GitHub Actions secret named `MONGODB_URI`.
- Do not mark the migration complete while any SQLAlchemy/Alembic dependency, import, migration step, or relational CI service remains.
