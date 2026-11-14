# Command Catalogue

This catalogue lists handlers that exist in the current repository. Commands are still subject to live Telegram permissions and group context checks.

| Command | Scope | Behavior | Access |
|---|---|---|---|
| /start | Private/group | Branded introduction | Everyone |
| /help | Private/group | Lists core and moderation commands | Everyone |
| /settings | Group | Reports current settings implementation status; changes no settings | Group admin |
| /about | Private/group | Product identity | Everyone |
| /id | Private/group | Returns chat and actor IDs | Everyone |
| /ping | Private/group | Basic process response | Everyone |
| /status | Private/group | Basic process status | Everyone |
| /ban | Group | Ban a replied-to member | Group admin + bot ban permission |\n| /tban DURATION [reason] | Group | Temporarily ban a replied-to member; Telegram enforces the expiry | Group admin + bot ban permission |
| /unban | Group | Unban replied user or numeric Telegram ID | Group admin + bot ban permission |
| /kick | Group | Ban then immediately unban a replied-to member | Group admin + bot ban permission |
| /mute | Group | Restrict a replied-to member for a duration (s/m/h/d, max 366 days) | Group admin + bot ban permission |
| /tmute DURATION [reason] | Group | Temporarily restrict a replied-to member; Telegram enforces the expiry | Group admin + bot ban permission |\n| /unmute | Group | Restore configured group default permissions | Group admin + bot ban permission |
| /warn | Group | Persist a warning for a replied-to member | Group admin |
| /warnings | Group | Show latest 10 warnings for a replied-to member | Group admin |
| /report | Group | Reply to a message with /report [reason]; save report and attempt to notify group admins privately | Group member |
| /reports | Group | Show latest 10 open reports for this group | Group admin |
| /adminlog | Group | Show latest 10 recorded moderation actions for this group | Group admin |
| /save NAME | Group | Save a replied-to text message as a group note | Group admin |
| /get NAME | Group | Retrieve a group note | Group member |
| /notes | Group | List saved notes | Group member |
| /filter keyword => response | Group | Create/update a keyword-triggered automatic response | Group admin |
| /stop KEYWORD | Group | Remove a keyword filter | Group admin |
| /filters | Group | List keyword filters | Group member |
| /welcome on/off | Group | Enable or disable new-member welcome messages | Group admin |
| /setwelcome TEXT | Group | Set welcome template; supports {first}, {name}, {id}, {mention} | Group admin |
| /purge COUNT | Group | Delete 1–100 messages from a replied-to message onward; requires delete permission | Group admin + bot delete permission |
| /lock CATEGORY | Group | Lock links, photos, videos, documents, stickers, or media | Group admin |
| /unlock CATEGORY | Group | Remove a category lock | Group admin |
| /locks | Group | Show active category locks | Group member |
| /blocklist add WORD | Group | Add a blocked term; matching text is deleted | Group admin |
| /blocklist del WORD | Group | Remove a blocked term | Group admin |
| /blocklist | Group | List blocked terms | Group member |
| /goodbye on/off | Group | Enable or disable member-leave notices | Group admin |
| /antiflood on/off | Group | Delete the 6th text message within 8 seconds from a user | Group admin |
| /closereport REPORT_ID | Group | Close an open report belonging to this group | Group admin |
| /resetwarnings | Group | Clear warnings for the replied-to member and record an audit action | Group admin |
| /captcha on/off | Group | Restrict new non-admin members until they pass a persisted 5-minute arithmetic challenge | Group admin |
| /antiraid on/off | Group | Alert admins after 5 joins in 30 seconds; no automatic bans | Group admin |
| /topic create NAME / close ID / reopen ID / delete ID | Forum supergroup | Manage forum topics with live user and bot permission checks | Group admin with Manage Topics |
| /export | Group | Export allowlisted settings for this group as versioned JSON | Group admin |
| /import | Group | Import a replied-to MASTER X JSON export into this group; strict allowlist and validation | Group admin |
| /fed create NAME | Group | Create a federation and explicitly opt this group in | Group admin |
| /fed join ID | Group | Explicitly opt this group into an existing federation | Group admin |
| /fed leave | Group | Remove this group from its federation | Group admin |
| /fed info | Group | Show this group's federation and opted-in member count | Group admin |\n| /fban USER_ID [reason] | Group | Record federation ban and apply it only to opted-in groups where the bot has Ban Users rights; skips targets who are admins | Group admin + bot Ban Users permission in origin; bot permission checked per destination |\n| /funban USER_ID | Group | Remove federation ban from opted-in groups; retains ledger if any destination is skipped or fails | Group admin + bot Ban Users permission in origin; bot permission checked per destination |
| /privacy | Group | Explain stored data and group-scoped erasure | Everyone |
| /privacy delete | Group | Delete records associated with your Telegram account in this group only | Everyone |
| /clean COUNT | Group | Delete 1–20 recent messages including the command, with explicit delete-right checks | Group admin + bot delete permission |
| /format STYLE TEXT | Private/group | Safely render bold, italic, code, or quote using escaped HTML | Everyone |

Command disabling is group-scoped. Administrators bypass disabled commands by default; /disableadmin on applies restrictions to admins too. /start, /help, /disable, /enable, /disabled and /disableadmin remain available as recovery controls. Only commands present in the command registry can be disabled. Privacy erasure is scoped to the requesting Telegram user and current group. Cleaning is limited to 20 recent messages. Formatting supports bold, italic, code, and quote with HTML escaping. Bot-to-bot command execution is disabled by default at the router boundary: bot-authored messages and callbacks are rejected, and anonymous sender identities fail closed. No admin/all mode or approval-review workflow is exposed. The export/import feature transfers only supported group settings; it does not copy reports, warnings, notes, filters, or user data.

Authorization is checked server-side. Group settings and report/admin-log queries are scoped by the current chat ID.
