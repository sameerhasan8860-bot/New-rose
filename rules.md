# Engineering and Security Rules

- Preserve working code; inspect before modifying. This repository was empty at initial audit.
- Small, reviewable modules; type hints for public interfaces.
- No fake handlers, no silent pass statements for advertised features.
- Every privileged action validates actor, chat, bot rights, target, and arguments.
- Every group-scoped database operation includes chat_id.
- Callbacks are untrusted input; validate format, ownership, and current permissions.
- Secrets never enter source control, logs, frontend bundles, or test fixtures.
- Use parameterized SQL / ORM expressions.
- Migrations must be additive by default; destructive changes require explicit approval and backup plan.
- AI classifications are advisory; never auto-ban solely on uncertain model output.
- External provider failure must degrade gracefully.
- Tests must be deterministic and must not call live Telegram or paid AI APIs by default.
- Do not claim VERIFIED without recorded evidence.
