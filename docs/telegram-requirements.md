# Telegram Requirements and Permissions

## Privacy mode
With privacy mode enabled, bots generally receive commands addressed to them, replies to their messages, service messages, and other limited update types—not every ordinary group message. A bot added as an administrator receives all group messages. Disabling privacy mode via BotFather also changes visibility, but the bot must be re-added for the setting to take effect.

## Required rights by module
- Read ordinary group messages: bot admin status or privacy mode disabled (and re-added).
- Delete messages: can_delete_messages.
- Ban/kick/restrict: can_restrict_members.
- Pin/unpin: can_pin_messages.
- Promote/demote: can_promote_members.
- Manage topics: can_manage_topics.
- Invite links: can_invite_users.
- Change group info: can_change_info.
Grant only rights required by enabled modules. Some rights and behavior vary by chat type and Bot API version; check live bot status before acting.

## Authorization
Telegram's visible command list is not security. Check current actor admin status and the exact required right for every moderation action. Revalidate callback actions too.
