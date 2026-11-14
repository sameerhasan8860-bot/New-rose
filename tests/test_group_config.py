import json
from types import SimpleNamespace

import pytest

from app.services.group_config import export_config, validate_import


def test_export_only_contains_allowlisted_group_settings():
    rows = [
        SimpleNamespace(key="welcome_enabled", value_json="true"),
        SimpleNamespace(key="locks", value_json='["links","photos"]'),
        SimpleNamespace(key="internal_secret", value_json='"must-not-export"'),
    ]
    payload = json.loads(export_config(rows))
    assert payload["format"] == "master-x-group-config"
    assert payload["settings"] == {"welcome_enabled": True, "locks": ["links", "photos"]}


def test_import_validates_and_normalizes_settings():
    result = validate_import(json.dumps({
        "format": "master-x-group-config",
        "version": 1,
        "settings": {"locks": ["photos", "links", "photos"], "captcha_enabled": True},
    }))
    assert result == {"locks": ["links", "photos"], "captcha_enabled": True}


@pytest.mark.parametrize("payload", [
    {"format": "other", "version": 1, "settings": {}},
    {"format": "master-x-group-config", "version": 2, "settings": {}},
    {"format": "master-x-group-config", "version": 1, "settings": {"is_owner": True}},
    {"format": "master-x-group-config", "version": 1, "settings": {"captcha_enabled": "yes"}},
    {"format": "master-x-group-config", "version": 1, "settings": {"locks": ["ban-everyone"]}},
])
def test_import_rejects_unknown_or_invalid_values(payload):
    with pytest.raises(ValueError):
        validate_import(json.dumps(payload))


def test_import_rejects_oversized_input():
    with pytest.raises(ValueError, match="too large"):
        validate_import(" " * 12001)
