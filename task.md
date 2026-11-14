# Development Roadmap

Status vocabulary: NOT STARTED, IN PROGRESS, IMPLEMENTED, TESTED, VERIFIED.

## Phase 1 — Audit and architecture
- [x] Inspect repository metadata and tree
- [x] Confirm repository was empty at audit time
- [x] Commit baseline docs and starter scaffold
- [x] Identify first CI failure from test logs and correct the Unicode brand assertion

## Phase 2 — Telegram core and database
- [x] Async SQLAlchemy database engine and schema models
- [x] Tenant-root groups and group-scoped settings repository
- [x] Initial moderation action and warning tables
- [x] Duplicate update guard backed by unique update IDs
- [x] Command registry with explicit access metadata
- [x] Live Telegram group-admin verification helper
- [x] Alembic migration environment and initial versioned migration
- [x] Wire migrations, database lifecycle, and update deduplication into polling runtime
- [x] Protect /settings with live Telegram admin verification
- [x] Latest moderation CI evidence: commits 2880bc2 and 1188adb passed
- [x] PostgreSQL integration and concurrent update insert tests (GitHub Actions PostgreSQL 16 service)

## Phase 3 — Rose compatibility (IN PROGRESS)
- [ ] Build command catalogue from authoritative documentation
- [x] Core moderation commands: ban, unban, kick, mute, unmute, warn, warnings
- [x] Group-scoped /report persistence and best-effort private admin notifications
- [x] Group-admin-only /reports and /adminlog (latest 10 records, current group only)
- [x] Group-scoped notes: /save, /get, /notes
- [x] Group-scoped keyword filters: /filter, /stop, /filters
- [x] Configurable new-member welcome messages and templates
- [x] Bounded /purge command (1–100 messages; admin and bot delete permission required)
- [x] Group category locks for links, photos, videos, documents, stickers, and media
- [x] Group-scoped blocked terms with automatic matching-message deletion
- [x] Configurable goodbye messages
- [x] Basic configurable text antiflood (6 messages per 8 seconds; in-process counter)
- [x] Live group-admin authorization helper tests
- [x] Mocked Telegram API permission tests for moderation and bounded clean handlers; reporting persistence/authorization tests exist (CI #192: 46 passed)
- [x] Opt-in persistent join CAPTCHA with per-group challenges, callback ownership checks, and saved/restored member permissions when Telegram exposes them
- [x] Opt-in antiraid alerts (5 joins / 30 seconds; persisted cross-worker event window and atomic alert deduplication; alert-only)
- [x] Forum topic create/close/reopen/delete with Telegram Manage Topics permission checks
- [x] Group-scoped /export and /import for allowlisted settings with strict schema validation
- [ ] Full federations/connections and cross-group moderation parity (consented membership plus /fban and /funban ledger/application now exist; per-target-group bot permission checks are enforced, but owner/admin roles, reasons/logs/banlist/subscriptions, durable retry queue, and private-group connections remain)
- [x] Group-scoped self-service privacy disclosure and erasure for warnings, reports, moderation actions, notes, filters, blocked terms, and CAPTCHA challenges
- [x] Bounded /clean (1–20 recent messages; actor and bot delete permissions required) and safe escaped /format helpers (bold, italic, code, quote)
- [ ] Full Rose-style bot-to-bot modes and admin review workflow (baseline security implemented: router rejects bot-authored messages/callbacks by default and fails closed for anonymous sender identities; bots cannot execute commands; configurable admin/all modes and review approvals are not implemented)
- [x] PostgreSQL integration and concurrent duplicate-delivery claim/lease tests (CI #138 passed; CI #192 also validated all migrations on SQLite and PostgreSQL)
- [x] Failed handlers no longer permanently consume update IDs (post-success persistence; external Telegram side effects are not exactly-once)
- [ ] Live Telegram test-group verification
