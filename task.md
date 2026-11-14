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
- [x] CI evidence: migration + all tests pass on commit 7757deb (rerun after latest moderation fixes pending)
- [ ] PostgreSQL integration and concurrency tests

## Phase 3 — Rose compatibility (IN PROGRESS)
- [ ] Build command catalogue from official docs
- [x] Core moderation commands: ban, unban, kick, mute, unmute, warn, warnings (group-admin gated; replied-to targets; action audit log)\n- [ ] Reports and admin-log browsing
- [ ] Greetings, notes, filters, locks, blocklists, CAPTCHA, antiflood, antiraid
- [ ] Federations, connections, topics, privacy, cleaning, formatting, import/export, bot-to-bot safeguards

## Phase 4 — Group Help compatibility
- [ ] Protection and CAPTCHA
- [ ] Anti-spam, anti-flood, banned words, night mode
- [ ] Welcome/goodbye, rules, moderation, custom commands, recurring messages
- [ ] Verify documented clone capabilities and limits

## Phase 5 — Iris research/integration
- [ ] Locate authoritative public Iris documentation/command catalogue
- [ ] Record only independently verified features
- [ ] Implement compatible features or document evidence gaps

## Phase 6 — Combot-style analytics/automation
- [ ] Event collection and analytics
- [ ] Trigger-condition-action engine
- [ ] Scheduler, XP, reputation, leaderboards, invite attribution

## Phase 7 — AI assistant
- [ ] Provider adapter and free-compatible configuration
- [ ] Mention/reply triggers and multilingual prompts
- [ ] Tenant-scoped expiring memory and privacy controls
- [ ] Moderation triage with human approval

## Phase 8 — Premium Telegram UX
- [ ] Callback menus, pagination, permission-aware views
- [ ] Original artwork and fallback media

## Phase 9 — Web dashboard
- [ ] Authentication and Telegram identity linking
- [ ] Group ownership verification and tenant isolation
- [ ] Settings, analytics, audit logs

## Phase 10 — Security and QA
- [ ] Abuse/rate limits, migrations, backups, recovery
- [ ] Integration/load/security tests

## Phase 11 — Deployment
- [ ] Durable DB, monitoring, deployment runbook
- [ ] Production readiness review
