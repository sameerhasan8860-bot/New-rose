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
| /ban | Group | Ban a replied-to member | Group admin + bot ban permission |
| /unban | Group | Unban replied user or numeric Telegram ID | Group admin + bot ban permission |
| /kick | Group | Ban then immediately unban a replied-to member | Group admin + bot ban permission |
| /mute | Group | Restrict a replied-to member for a duration (s/m/h/d, max 366 days) | Group admin + bot ban permission |
| /unmute | Group | Restore configured group default permissions | Group admin + bot ban permission |
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

Not yet implemented: federations, connections, privacy controls, cleaning, formatting helpers, and bot-to-bot safeguards. The export/import feature transfers only supported group settings; it does not copy reports, warnings, notes, filters, or user data.

Authorization is checked server-side. Group settings and report/admin-log queries are scoped by the current chat ID.
