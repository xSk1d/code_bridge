from __future__ import annotations

import json
from pathlib import Path

from ccb_start_config import (
    DEFAULT_PRIMARY_PROVIDER,
    DEFAULT_PROVIDERS,
    ensure_default_start_config,
    load_start_config,
)


def test_load_start_config_keeps_primary_provider_when_present(tmp_path: Path) -> None:
    cfg_dir = tmp_path / ".ccb"
    cfg_dir.mkdir()
    payload = {
        "providers": ["codex", "claude", "gemini"],
        "primary_provider": "gemini",
    }
    (cfg_dir / "ccb.config").write_text(json.dumps(payload), encoding="utf-8")

    config = load_start_config(tmp_path)

    assert config.data["providers"] == ["codex", "claude", "gemini"]
    assert config.data["primary_provider"] == "gemini"


def test_load_start_config_drops_invalid_primary_provider(tmp_path: Path) -> None:
    cfg_dir = tmp_path / ".ccb"
    cfg_dir.mkdir()
    payload = {
        "providers": ["codex", "claude"],
        "primary_provider": "gemini",
    }
    (cfg_dir / "ccb.config").write_text(json.dumps(payload), encoding="utf-8")

    config = load_start_config(tmp_path)

    assert config.data["providers"] == ["codex", "claude"]
    assert "primary_provider" not in config.data


def test_ensure_default_start_config_sets_gemini_primary(tmp_path: Path) -> None:
    path, created = ensure_default_start_config(tmp_path)

    assert created is True
    assert path is not None

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["providers"] == DEFAULT_PROVIDERS
    assert payload["primary_provider"] == DEFAULT_PRIMARY_PROVIDER
