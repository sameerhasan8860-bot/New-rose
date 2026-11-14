# Database Schema Plan

Production target: PostgreSQL. SQLite is acceptable for isolated development tests only.

All tenant-owned tables include chat_id and have composite indexes/constraints beginning with chat_id.

| Table | Key fields | Isolation / notes |
|---|---|---|
| users | user_id, username, display_name, created_at | Global identity only; no group private data |
| groups | chat_id, title, created_at, status | Tenant root |
| group_settings | chat_id, key, value_json, updated_at | PK(chat_id,key) |
| group_admins | chat_id, user_id, role, verified_at | Telegram role cache; revalidate live for actions |
| moderation_actions | id, chat_id, actor_id, target_id, action, expires_at | Audit immutable action record |
| warnings | id, chat_id, user_id, actor_id, reason, created_at | Index(chat_id,user_id) |
| filters | id, chat_id, trigger, match_type, response_json, enabled | Unique(chat_id,trigger) |
| notes | id, chat_id, name, content_json, visibility | Unique(chat_id,name) |
| custom_commands | id, chat_id, name, action_json, enabled | Unique(chat_id,name) |
| welcome_settings | chat_id, enabled, template_json | One row per chat |
| goodbye_settings | chat_id, enabled, template_json | One row per chat |
| locks | chat_id, lock_type, enabled, policy_json | PK(chat_id,lock_type) |
| blocklists | id, chat_id, pattern, match_type, action | Index(chat_id,pattern) |
| allowlists | id, chat_id, pattern, scope | Index(chat_id,scope) |
| captcha_sessions | id, chat_id, user_id, expires_at, state | Unique(chat_id,user_id) |
| reports | id, chat_id, reporter_id, target_id, message_id, status | Index(chat_id,status) |
| scheduled_messages | id, chat_id, payload_json, schedule_at, recurrence, enabled | Scheduler lease required |
| automation_rules | id, chat_id, trigger_json, conditions_json, actions_json, enabled | Tenant-scoped |
| analytics_events | id, chat_id, user_id, event_type, occurred_at | Partition/retention policy |
| user_xp | chat_id, user_id, xp, level | PK(chat_id,user_id) |
| reputation | chat_id, user_id, score | PK(chat_id,user_id) |
| ai_settings | chat_id, settings_json, enabled | Per-group provider policy |
| ai_conversations | id, chat_id, user_id, expires_at | Never cross tenant |
| ai_memory | id, chat_id, user_id, content, expires_at | Opt-in, bounded, deletable |
| audit_logs | id, chat_id nullable, actor_id, event, metadata_json | Global events may have null chat_id |
| owner_settings | key, value_json | Global owner only |

## Migration rules
- Use versioned Alembic migrations once ORM models are introduced.
- Additive migrations by default.
- Back up before destructive changes.
- Never cascade-delete audit records by default.
- Enforce foreign keys and tenant-aware unique constraints.
