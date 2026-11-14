"""MongoDB connection lifecycle and idempotent index bootstrap.

Runtime cutover is deferred until all SQLAlchemy-backed handlers and services
have been ported.
"""
from __future__ import annotations

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase


class MongoDatabase:
    """Own one async MongoDB client and expose its database."""

    def __init__(self, uri: str, database_name: str = "master_x") -> None:
        if not uri or not uri.strip():
            raise ValueError("MONGODB_URI is required for MongoDB")
        if not uri.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("MONGODB_URI must start with mongodb:// or mongodb+srv://")
        if not database_name or not database_name.strip():
            raise ValueError("MONGODB_DATABASE must not be empty")
        self.client = AsyncMongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=10000)
        self.database: AsyncDatabase = self.client[database_name.strip()]

    async def ping(self) -> None:
        await self.client.admin.command("ping")

    async def ensure_indexes(self) -> None:
        """Create idempotent indexes, including group-tenant uniqueness."""
        specs = {
            "groups": [([("chat_id", ASCENDING)], {"unique": True})],
            "group_settings": [([("chat_id", ASCENDING), ("key", ASCENDING)], {"unique": True})],
            "group_admins": [([("chat_id", ASCENDING), ("user_id", ASCENDING)], {"unique": True})],
            "processed_updates": [([("update_id", ASCENDING)], {"unique": True})],
            "update_claims": [([("update_id", ASCENDING)], {"unique": True})],
            "moderation_actions": [([("chat_id", ASCENDING), ("created_at", DESCENDING)], {})],
            "warnings": [([("chat_id", ASCENDING), ("user_id", ASCENDING)], {})],
            "reports": [([("chat_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)], {})],
            "notes": [([("chat_id", ASCENDING), ("name", ASCENDING)], {"unique": True})],
            "group_filters": [([("chat_id", ASCENDING), ("trigger", ASCENDING)], {"unique": True})],
            "blocked_terms": [([("chat_id", ASCENDING), ("term", ASCENDING)], {"unique": True})],
            "captcha_challenges": [([("chat_id", ASCENDING), ("user_id", ASCENDING), ("status", ASCENDING)], {})],
            "federations": [([("name", ASCENDING)], {"unique": True})],
            "federation_groups": [([("chat_id", ASCENDING)], {"unique": True}), ([("federation_id", ASCENDING), ("consented_at", ASCENDING)], {})],
            "federation_bans": [([("federation_id", ASCENDING), ("user_id", ASCENDING)], {"unique": True})],
            "raid_join_events": [([("chat_id", ASCENDING), ("joined_at", DESCENDING)], {})],
            "raid_alerts": [([("chat_id", ASCENDING), ("threshold_event_id", ASCENDING)], {"unique": True})],
        }
        for name, indexes in specs.items():
            collection = self.database[name]
            for keys, options in indexes:
                await collection.create_index(keys, **options)

    async def close(self) -> None:
        await self.client.close()
