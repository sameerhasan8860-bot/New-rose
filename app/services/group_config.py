"""Validation helpers for safe, group-scoped configuration transfer."""
import json

ALLOWED_SETTINGS = {
    "locks",
    "antiflood_enabled",
    "welcome_enabled",
    "welcome_template",
    "antiraid_enabled",
    "captcha_enabled",
    "goodbye_enabled",
}
LOCK_CATEGORIES = {"links", "photos", "videos", "documents", "stickers", "media"}


def export_config(rows) -> str:
    payload = {
        "format": "master-x-group-config",
        "version": 1,
        "settings": {
            row.key: json.loads(row.value_json)
            for row in rows
            if row.key in ALLOWED_SETTINGS
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def validate_import(raw: str) -> dict:
    if len(raw) > 12000:
        raise ValueError("Configuration is too large (maximum 12,000 characters).")
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Reply with valid JSON configuration.") from exc
    if not isinstance(payload, dict) or payload.get("format") != "master-x-group-config" or payload.get("version") != 1:
        raise ValueError("Unsupported configuration format or version.")
    settings = payload.get("settings")
    if not isinstance(settings, dict) or len(settings) > len(ALLOWED_SETTINGS):
        raise ValueError("Invalid settings object.")
    clean = {}
    for key, value in settings.items():
        if key not in ALLOWED_SETTINGS:
            raise ValueError(f"Unsupported setting: {key}")
        if key == "locks":
            if not isinstance(value, list) or any(not isinstance(item, str) or item not in LOCK_CATEGORIES for item in value):
                raise ValueError("Invalid lock categories.")
            clean[key] = sorted(set(value))
        elif key == "welcome_template":
            if not isinstance(value, str) or len(value) > 3500:
                raise ValueError("Welcome template must be text up to 3,500 characters.")
            clean[key] = value
        else:
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be true or false.")
            clean[key] = value
    return clean
