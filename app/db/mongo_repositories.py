"""MongoDB-native persistence primitives used during the backend migration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.db.mongo import MongoDatabase


class MongoRepository:
    """Small tenant-aware repository; group-owned operations always include chat_id."""

    def __init__(self, database: MongoDatabase) -> None:
        self.db = database.database

    async def ensure_group(self, chat_id: int, title: str = "") -> dict[str, Any]:
        await self.db.groups.update_one(
            {"chat_id": int(chat_id)},
            {"$set": {"title": title} if title else {}, "$setOnInsert": {
                "chat_id": int(chat_id), "title": title, "status": "active",
                "created_at": datetime.now(timezone.utc),
            }},
            upsert=True,
        )
        return await self.db.groups.find_one({"chat_id": int(chat_id)})

    async def get_setting(self, chat_id: int, key: str, default: Any = None) -> Any:
        row = await self.db.group_settings.find_one({"chat_id": int(chat_id), "key": key})
        return default if row is None else row.get("value", default)

    async def set_setting(self, chat_id: int, key: str, value: Any) -> None:
        await self.ensure_group(chat_id)
        await self.db.group_settings.update_one(
            {"chat_id": int(chat_id), "key": key},
            {"$set": {"value": value, "updated_at": datetime.now(timezone.utc)},
             "$setOnInsert": {"chat_id": int(chat_id), "key": key}},
            upsert=True,
        )

    async def mark_update_processed(self, update_id: int) -> bool:
        try:
            await self.db.processed_updates.insert_one({
                "update_id": int(update_id), "processed_at": datetime.now(timezone.utc),
            })
            return True
        except DuplicateKeyError:
            return False

    async def claim_update(self, update_id: int, owner_token: str, lease_seconds: int = 300) -> bool:
        if lease_seconds < 1:
            raise ValueError("lease_seconds must be positive")
        now = datetime.now(timezone.utc)
        try:
            await self.db.update_claims.find_one_and_update(
                {"update_id": int(update_id), "$or": [
                    {"expires_at": {"$lte": now}}, {"expires_at": {"$exists": False}},
                ]},
                {"$set": {"owner_token": owner_token,
                          "expires_at": now + timedelta(seconds=lease_seconds)}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return True
        except DuplicateKeyError:
            # An unexpired lease already owns this update ID.
            return False

    async def release_update_claim(self, update_id: int, owner_token: str) -> bool:
        result = await self.db.update_claims.delete_one({
            "update_id": int(update_id), "owner_token": owner_token,
        })
        return result.deleted_count == 1

    async def delete_user_group_records(self, chat_id: int, user_id: int) -> dict[str, int]:
        """Erase only this user's records in the requested group."""
        chat_id, user_id = int(chat_id), int(user_id)
        specifications = {
            "warnings": {"chat_id": chat_id, "$or": [{"user_id": user_id}, {"actor_id": user_id}]},
            "reports": {"chat_id": chat_id, "$or": [{"reporter_id": user_id}, {"target_id": user_id}]},
            "moderation_actions": {"chat_id": chat_id, "$or": [{"actor_id": user_id}, {"target_id": user_id}]},
            "notes": {"chat_id": chat_id, "creator_id": user_id},
            "group_filters": {"chat_id": chat_id, "creator_id": user_id},
            "blocked_terms": {"chat_id": chat_id, "creator_id": user_id},
            "captcha_challenges": {"chat_id": chat_id, "user_id": user_id},
        }
        counts: dict[str, int] = {}
        for collection, query in specifications.items():
            result = await self.db[collection].delete_many(query)
            counts[collection] = result.deleted_count
        return counts
