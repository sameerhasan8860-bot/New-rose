# MASTER X

A modular Telegram community-management platform.

## Current runtime

- Python 3.12 + aiogram 3 polling bot.
- Current production runtime is still SQLAlchemy-backed; MongoDB migration is in progress on `feature/mongodb-migration`.
- MongoDB Atlas support is being added through PyMongo's async client. Do not switch the worker to MongoDB until all handlers/services are ported and MongoDB CI passes.
- GitHub Actions provides CI and an explicitly started, bounded bot worker.

## MongoDB migration

See [mongodb_migration.md](mongodb_migration.md). The final worker configuration will require `BOT_TOKEN` and `MONGODB_URI`; it is not enabled until the SQLAlchemy/Alembic code path has been fully removed and verified.

## GitHub Actions

Start the worker manually from Actions → MASTER X Bot Worker → Run workflow. GitHub-hosted runners are temporary CI machines, not guaranteed 24/7 hosting; runner limits, account minute quotas, and ephemeral disk apply.

## Required Telegram setup

For full moderation and ordinary group-message processing, add the bot as an administrator with only the rights required by enabled modules. Privacy mode affects which group messages a non-admin bot receives. See `docs/telegram-requirements.md`.

## Roadmap and truthfulness

See `task.md`, `feature_parity.md`, and `testing.md`. A feature is not VERIFIED until an actual test or Telegram integration test is recorded.
