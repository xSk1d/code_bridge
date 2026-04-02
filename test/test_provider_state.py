from __future__ import annotations

import json
from pathlib import Path

from provider_state import classify_provider_outcome, record_provider_outcome


def test_classify_provider_outcome_detects_limit_signal() -> None:
    info = classify_provider_outcome("failed", "429 Too many requests. Retry after 12 seconds.")
    assert info["availability"] == "limited"
    assert info["limit_detected"] is True
    assert info["retry_after_s"] == 12


def test_record_provider_outcome_writes_state_file(tmp_path: Path) -> None:
    cfg_dir = tmp_path / ".ccb"
    cfg_dir.mkdir()

    path = record_provider_outcome(
        tmp_path,
        "claude",
        status="failed",
        reply="Usage limit reached for this account.",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["provider"] == "claude"
    assert payload["availability"] == "limited"
    assert payload["limit_detected"] is True
    assert payload["consecutive_failures"] == 1

    record_provider_outcome(tmp_path, "claude", status="completed", reply="All good")
    payload2 = json.loads(path.read_text(encoding="utf-8"))
    assert payload2["availability"] == "available"
    assert payload2["consecutive_failures"] == 0
