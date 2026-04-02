from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional, Tuple

from session_utils import legacy_project_config_dir, project_config_dir


CONFIG_FILENAME = "ccb.config"
DEFAULT_PROVIDERS = ["gemini", "claude", "codex"]
DEFAULT_PRIMARY_PROVIDER = "gemini"
DEFAULT_CMD_CONFIG = {"enabled": True, "title": "CCB-Control"}


@dataclass
class StartConfig:
    data: dict
    path: Optional[Path] = None


_ALLOWED_PROVIDERS = {"codex", "gemini", "opencode", "claude", "droid"}
_CMD_ALIASES = {"cmd", "central", "control"}


def _normalize_primary_provider(raw: object) -> str | None:
    value = str(raw or "").strip().lower()
    if value in _ALLOWED_PROVIDERS:
        return value
    return None


def _normalize_cmd_config_value(raw: object) -> object:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        data = dict(raw)
        title = str(data.get("title") or data.get("name") or "CCB-Control").strip() or "CCB-Control"
        start_cmd = str(data.get("start_cmd") or data.get("command") or data.get("cmd") or "").strip()
        enabled = data.get("enabled")
        if enabled is None:
            enabled = True
        return {
            "enabled": bool(enabled),
            "title": title,
            "start_cmd": start_cmd,
        }
    return None


def _parse_tokens(raw: str) -> list[str]:
    if not raw:
        return []
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line
        if "//" in stripped:
            stripped = stripped.split("//", 1)[0]
        if "#" in stripped:
            stripped = stripped.split("#", 1)[0]
        lines.append(stripped)
    cleaned = " ".join(lines)
    cleaned = re.sub(r"[\[\]\{\}\"']", " ", cleaned)
    parts = re.split(r"[,\s]+", cleaned)
    return [p for p in (part.strip() for part in parts) if p]


def _normalize_providers(tokens: list[str]) -> tuple[list[str], bool]:
    providers: list[str] = []
    seen: set[str] = set()
    cmd_enabled = False
    for raw in tokens:
        token = str(raw).strip().lower()
        if not token:
            continue
        if token in _CMD_ALIASES:
            cmd_enabled = True
            continue
        if token not in _ALLOWED_PROVIDERS:
            continue
        if token in seen:
            continue
        seen.add(token)
        providers.append(token)
    return providers, cmd_enabled


def _parse_config_obj(obj: object) -> dict:
    if isinstance(obj, dict):
        data = dict(obj)
        if "cmd" not in data:
            for alias in ("central_input", "control_pane", "central"):
                if alias in data:
                    normalized_cmd = _normalize_cmd_config_value(data.get(alias))
                    if normalized_cmd is not None:
                        data["cmd"] = normalized_cmd
                    break
        else:
            normalized_cmd = _normalize_cmd_config_value(data.get("cmd"))
            if normalized_cmd is not None:
                data["cmd"] = normalized_cmd
        raw_providers = data.get("providers")
        tokens: list[str] = []
        if isinstance(raw_providers, str):
            tokens = _parse_tokens(raw_providers)
        elif isinstance(raw_providers, list):
            tokens = [str(p) for p in raw_providers if p is not None]
        elif raw_providers is not None:
            tokens = [str(raw_providers)]

        if tokens:
            providers, cmd_enabled = _normalize_providers(tokens)
            data["providers"] = providers
            if cmd_enabled and "cmd" not in data:
                data["cmd"] = True
        primary_provider = (
            _normalize_primary_provider(data.get("primary_provider"))
            or _normalize_primary_provider(data.get("coordinator_provider"))
            or _normalize_primary_provider(data.get("anchor_provider"))
        )
        if primary_provider and primary_provider in data.get("providers", []):
            data["primary_provider"] = primary_provider
        else:
            data.pop("primary_provider", None)
        return data

    if isinstance(obj, list):
        tokens = [str(p) for p in obj if p is not None]
        providers, cmd_enabled = _normalize_providers(tokens)
        data: dict = {"providers": providers}
        if cmd_enabled:
            data["cmd"] = True
        return data

    if isinstance(obj, str):
        tokens = _parse_tokens(obj)
        providers, cmd_enabled = _normalize_providers(tokens)
        data = {"providers": providers}
        if cmd_enabled:
            data["cmd"] = True
        return data

    return {}


def _read_config(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return {}
    if not raw.strip():
        return {}
    try:
        obj = json.loads(raw)
    except Exception:
        obj = None
    if obj is None:
        tokens = _parse_tokens(raw)
        providers, cmd_enabled = _normalize_providers(tokens)
        data: dict = {"providers": providers}
        if cmd_enabled:
            data["cmd"] = True
        return data
    return _parse_config_obj(obj)


def _config_paths(work_dir: Path) -> Tuple[Path, Path, Path]:
    primary = project_config_dir(work_dir) / CONFIG_FILENAME
    legacy = legacy_project_config_dir(work_dir) / CONFIG_FILENAME
    global_path = Path.home() / ".ccb" / CONFIG_FILENAME
    return primary, legacy, global_path


def load_start_config(work_dir: Path) -> StartConfig:
    primary, legacy, global_path = _config_paths(work_dir)
    if primary.exists():
        return StartConfig(data=_read_config(primary), path=primary)
    if legacy.exists():
        return StartConfig(data=_read_config(legacy), path=legacy)
    if global_path.exists():
        return StartConfig(data=_read_config(global_path), path=global_path)
    return StartConfig(data={}, path=None)


def ensure_default_start_config(work_dir: Path) -> Tuple[Optional[Path], bool]:
    primary, legacy, _global_path = _config_paths(work_dir)
    if primary.exists():
        return primary, False
    if legacy.exists():
        return legacy, False
    target = primary
    if not primary.parent.exists() and legacy.parent.is_dir():
        target = legacy
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "providers": list(DEFAULT_PROVIDERS),
                "primary_provider": DEFAULT_PRIMARY_PROVIDER,
                "cmd": dict(DEFAULT_CMD_CONFIG),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        target.write_text(payload, encoding="utf-8")
        return target, True
    except Exception:
        return None, False
