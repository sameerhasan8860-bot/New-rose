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
- [ ] PostgreSQL integration and concurrency tests

## Phase 3 — Rose compatibility (IN PROGRESS)
- [ ] Build command catalogue from authoritative documentation
- [x] Core moderation commands: ban, unban, kick, mute, unmute, warn, warnings
- [x] Group-scoped /report persistence and best-effort private admin notifications
- [x] Group-admin-only /reports and /adminlog (latest 10 records, current group only)
- [x] Group-scoped notes: /save, /get, /notes
- [x] Group-scoped keyword filters: /filter, /stop, /filters
- [x] Configurable new-member welcome messages and templates
- [x] Bounded /purge command (1–100 messages; admin and bot delete permission required)
- [ ] Mocked Telegram API tests for moderation and reporting authorization paths
- [ ] Greetings, notes, filters, locks, blocklists, CAPTCHA, antiflood, antiraid
- [ ] Federations, connections, topics, privacy, cleaning, formatting, import/export, bot-to-bot safeguards
- [ ] PostgreSQL integration, retry-safe update processing, and live test-group verification
