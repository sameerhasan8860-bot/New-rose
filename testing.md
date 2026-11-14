# Testing Strategy and Evidence

## Phase 1 test plan
- Configuration rejects missing BOT_TOKEN.
- /start and /help format without external network.
- ID response handles private/group chat identifiers.
- Unknown command behavior is safe.
- No secret is included in status output.
- CI installs pinned dependencies and runs pytest.

## Module test requirements
Every feature needs unit tests for parsing, authorization, tenant isolation, DB behavior, and failure handling. Telegram integration tests must use a dedicated test group and record date, bot rights, expected result, and observed result. AI tests use a mocked provider by default.

## Status policy
A test passing locally is TESTED only for that test scope. VERIFIED requires real Telegram behavior evidence. No status is promoted on the basis of code inspection alone.

## Evidence log
No tests have been run yet in the initial repository audit. Update this file with workflow run URL, commit SHA, Python version, test count, and outcome after CI executes.
