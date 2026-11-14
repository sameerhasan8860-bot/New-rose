# Development Roadmap

Status vocabulary: NOT STARTED, IN PROGRESS, IMPLEMENTED, TESTED, VERIFIED.

## Phase 1 — Audit and architecture
- [x] Inspect repository metadata and tree
- [x] Confirm repository was empty at audit time
- [x] Commit baseline docs and starter scaffold
- [x] Run CI and capture first test evidence (initial failure found: pytest import path; fixed in Phase 2 CI config)

## Phase 2 — Telegram core and database
- [x] Async SQLAlchemy database engine and schema bootstrap
- [x] Initial tenant-root, group settings, admin cache, processed-update, moderation and warning models
- [x] Chat-scoped settings repository
- [x] Duplicate update guard backed by a unique update ID
- [x] Command registry with explicit access metadata and implemented status
- [x] Live Telegram group-admin authorization helper
- [ ] Alembic migration environment and first versioned migration
- [ ] Wire database lifecycle and idempotency middleware into polling runtime
- [ ] Wire admin authorization into privileged command handlers
- [ ] PostgreSQL integration test and concurrency test

## Phase 3 — Rose compatibility
- [ ] Build command catalogue from official docs
- [ ] Moderation, warnings, reports, admin logs
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
