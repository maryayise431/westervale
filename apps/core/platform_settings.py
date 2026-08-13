import json
from pathlib import Path

PLATFORM_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / 'config' / 'platform_settings.json'

_DEFAULTS = {
    'active_holdings': None,
}


def get_platform_settings():
    if not PLATFORM_SETTINGS_FILE.exists():
        return dict(_DEFAULTS)
    try:
        with open(PLATFORM_SETTINGS_FILE, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update({key: value for key, value in data.items() if key in _DEFAULTS})
    return merged


def save_platform_settings(updates):
    data = get_platform_settings()
    for key, value in updates.items():
        if key in _DEFAULTS:
            data[key] = value
    PLATFORM_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PLATFORM_SETTINGS_FILE, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)
    return data
