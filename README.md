# MASTER X

A modular Telegram community-management platform. The repository is currently in Phase 1: architecture, safe bot foundation, and deployment workflow.

## Current scope
- Python 3.12 + aiogram 3 polling bot
- SQLite for local smoke tests; PostgreSQL is the intended persistent production database
- GitHub Actions for CI and an explicitly started, bounded bot worker
- Feature modules are added only with real handlers, authorization, persistence, and tests

## Quick start
1. Create a bot with @BotFather.
2. Copy `.env.example` to `.env` and set `BOT_TOKEN`.
3. Install: `pip install -r requirements.txt`
4. Run: `python -m app`
5. Test: `pytest -q`

## GitHub Actions
Add repository secret `BOT_TOKEN`. Add `DATABASE_URL` only when using an external persistent database. Start the worker manually from Actions → MASTER X Bot Worker → Run workflow. GitHub-hosted runners are temporary CI machines, not guaranteed 24/7 hosting; runner limits, account minute quotas, and ephemeral disk apply. SQLite data on a hosted runner is not durable between runs.

## Required Telegram setup
For full moderation and ordinary group-message processing, add the bot as an administrator with only the rights required by enabled modules. Privacy mode affects which group messages a non-admin bot receives. See `docs/telegram-requirements.md`.

## Roadmap and truthfulness
See `task.md`, `feature_parity.md`, and `testing.md`. A feature is not VERIFIED until an actual test or Telegram integration test is recorded.
