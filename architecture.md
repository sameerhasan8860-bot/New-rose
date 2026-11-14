# Architecture

## Stack
- Python 3.12, aiogram 3 asynchronous Telegram Bot API framework.
- Pydantic Settings for validated environment configuration.
- SQLAlchemy 2 async ORM; SQLite + aiosqlite for isolated tests, PostgreSQL + asyncpg for durable deployment.
- Alembic is selected for versioned schema migrations; migration setup is pending.
- pytest for unit tests; GitHub Actions for CI and bounded manual worker execution.

## Layers
1. Telegram adapter: aiogram routers, callbacks, keyboards, update parsing.
2. Application services: use cases, authorization, command registry.
3. Domain: group/user settings, moderation policies, automation rules.
4. Persistence: async repositories and migrations; tenant-scoped keys.
5. Integrations: AI provider interface, scheduler, optional dashboard API.

## Tenant isolation
Every group-owned record includes chat_id and every tenant repository operation requires chat_id. User memory is scoped by (chat_id, user_id). Global owner settings are a separate namespace. No implicit cross-group reads. Cached group admin rows are informational only; privileged actions re-check Telegram live membership and rights.

## Runtime
Long polling is the deployment path. Only one active polling worker should use a bot token at a time. GitHub Actions is a temporary worker; its local filesystem is ephemeral. Production persistence requires external PostgreSQL or another durable database. Never rely on runner SQLite for continuity.

## Security boundaries
- Never trust command menu visibility or callback payloads as authorization.
- Re-check Telegram admin role and rights for every privileged operation.
- Store secrets only in environment variables / GitHub Secrets.
- Do not log tokens, full private conversation content, or sensitive provider responses.
- AI provider calls go through a narrow adapter with timeouts, limits, and explicit opt-in.
