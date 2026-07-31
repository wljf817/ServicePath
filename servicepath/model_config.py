import json
import re
from pathlib import Path

from servicepath.settings import (
    SettingsError,
    validate_openai_api_mode,
    validate_openai_base_url,
    validate_servicepath_server_token,
    validate_servicepath_server_url,
)


PRESET_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z", re.ASCII)


def _provider(data):
    if not isinstance(data, dict):
        raise SettingsError("Provider configuration must be an object.")

    api_key = str(data.get("api_key", "")).strip()
    model = str(data.get("model", "")).strip()
    if not api_key:
        raise SettingsError("Provider API key is required.")
    if not model or len(model) > 200:
        raise SettingsError("Provider model name is invalid.")

    return {
        "api_key": api_key,
        "model": model,
        "base_url": validate_openai_base_url(data.get("base_url", "")),
        "api_mode": validate_openai_api_mode(
            data.get("api_mode", "responses")
        ),
    }


def _preset_identity(data, used_ids, label):
    if not isinstance(data, dict):
        raise SettingsError(f"Each preset {label} must be an object.")
    preset_id = str(data.get("id", "")).strip()
    name = str(data.get("name", "")).strip()
    if not PRESET_ID.fullmatch(preset_id) or preset_id in used_ids:
        raise SettingsError(f"Preset {label} ID is invalid or duplicated.")
    if not name or len(name) > 100:
        raise SettingsError(f"Preset {label} name is invalid.")
    return preset_id, name


def _remote_server(data):
    server_url = validate_servicepath_server_url(data.get("url", ""))
    token = validate_servicepath_server_token(data.get("token", ""))
    if not server_url or not token:
        raise SettingsError("Preset server URL and token are required.")
    return {"url": server_url, "token": token}


def load_server_config(path):
    """Load private model presets, server presets, and the inbound token."""
    path = Path(path)
    if not path.is_file():
        return {"server_token": "", "presets": {}, "servers": {}}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SettingsError("Server configuration file is invalid.") from error
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("models", []), list)
        or not isinstance(data.get("servers", []), list)
    ):
        raise SettingsError("Server configuration file is invalid.")

    presets = {}
    for item in data.get("models", []):
        preset_id, name = _preset_identity(item, presets, "model")
        presets[preset_id] = {"id": preset_id, "name": name, **_provider(item)}

    servers = {}
    for item in data.get("servers", []):
        server_id, name = _preset_identity(item, servers, "server")
        servers[server_id] = {
            "id": server_id,
            "name": name,
            **_remote_server(item),
        }

    return {
        "server_token": validate_servicepath_server_token(
            data.get("server_token", "")
        ),
        "presets": presets,
        "servers": servers,
    }


def public_presets(config):
    return [
        {
            "id": preset["id"],
            "name": preset["name"],
            "model": preset["model"],
            "api_mode": preset["api_mode"],
        }
        for preset in config["presets"].values()
    ]


def public_servers(config):
    return [
        {"id": server["id"], "name": server["name"], "url": server["url"]}
        for server in config["servers"].values()
    ]


def resolve_server(config, server_id):
    server = config["servers"].get(str(server_id))
    if not server:
        raise SettingsError("Selected server preset is unavailable.")
    return {"url": server["url"], "token": server["token"]}


def resolve_provider(config, selection):
    if not isinstance(selection, dict):
        raise SettingsError("Provider selection must be an object.")

    selection_type = selection.get("type")
    if selection_type == "preset":
        preset = config["presets"].get(str(selection.get("id", "")))
        if not preset:
            raise SettingsError("Selected preset model is unavailable.")
        return {key: preset[key] for key in ("api_key", "model", "base_url", "api_mode")}
    if selection_type == "custom":
        return _provider(selection)
    raise SettingsError("Provider selection is invalid.")
