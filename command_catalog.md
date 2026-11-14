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
| /get NAME | Group | Retrieve a saved note | Group member |
| /notes | Group | List saved notes | Group member |
| /filter keyword => response | Group | Create/update a keyword-triggered automatic response | Group admin |
| /stop KEYWORD | Group | Remove a keyword filter | Group admin |
| /filters | Group | List keyword filters | Group member |
| /welcome on/off | Group | Enable or disable new-member welcome messages | Group admin |
| /setwelcome TEXT | Group | Set welcome template; supports {first}, {name}, {id}, {mention} | Group admin |
| /purge COUNT | Group | Delete 1–100 messages from a replied-to message onward; requires delete permission | Group admin + bot delete permission |

Not yet implemented: goodbye, locks, blocklists, CAPTCHA, antiflood, antiraid, federations, connections, topics, privacy, cleaning, formatting, import/export, and bot-to-bot safeguards. Notes, keyword filters, and configurable new-member welcome messages are implemented in the current build. Do not advertise these as working.

Authorization is always checked server-side. Report and admin-log queries are scoped by the current chat ID.
