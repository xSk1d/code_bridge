from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from session_utils import resolve_project_config_dir


_LIMIT_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\b429\b"), "limited", "http_429"),
    (re.compile(r"too many requests", re.IGNORECASE), "limited", "too_many_requests"),
    (re.compile(r"rate limit", re.IGNORECASE), "limited", "rate_limit"),
    (re.compile(r"usage limit", re.IGNORECASE), "limited", "usage_limit"),
    (re.compile(r"quota", re.IGNORECASE), "limited", "quota"),
    (re.compile(r"credit(?:s)? exhausted", re.IGNORECASE), "limited", "credits_exhausted"),
    (re.compile(r"exceeded your current quota", re.IGNORECASE), "limited", "quota_exceeded"),
    (re.compile(r"resource has been exhausted", re.IGNORECASE), "limited", "resource_exhausted"),
    (re.compile(r"daily limit", re.IGNORECASE), "limited", "daily_limit"),
    (re.compile(r"monthly limit", re.IGNORECASE), "limited", "monthly_limit"),
    (re.compile(r"free tier", re.IGNORECASE), "limited", "free_tier_limit"),
]

_RETRY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"retry after[: ]+(\d+)\s*(?:s|sec|secs|second|seconds)\b", re.IGNORECASE),
    re.compile(r"retry in[: ]+(\d+)\s*(?:s|sec|secs|second|seconds)\b", re.IGNORECASE),
    re.compile(r"retry after[: ]+(\d+)\s*(?:m|min|mins|minute|minutes)\b", re.IGNORECASE),
    re.compile(r"retry in[: ]+(\d+)\s*(?:m|min|mins|minute|minutes)\b", re.IGNORECASE),
]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def provider_state_dir(work_dir: str | Path) -> Path:
    return resolve_project_config_dir(Path(work_dir)) / "provider-state"


def provider_state_path(work_dir: str | Path, provider: str) -> Path:
    return provider_state_dir(work_dir) / f"{str(provider or '').strip().lower()}.json"


def load_provider_state(work_dir: str | Path, provider: str) -> dict[str, Any]:
    path = provider_state_path(work_dir, provider)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _parse_retry_after_seconds(reply: str) -> int | None:
    text = str(reply or "")
    for pattern in _RETRY_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            value = int(m.group(1))
        except Exception:
            continue
        if "minute" in pattern.pattern or r"\s*(?:m|min|mins|minute|minutes)" in pattern.pattern:
            return value * 60
        return value
    return None


def classify_provider_outcome(status: str, reply: str) -> dict[str, Any]:
    normalized_status = (status or "").strip().lower() or "completed"
    text = str(reply or "")

    for pattern, availability, reason in _LIMIT_PATTERNS:
        if pattern.search(text):
            return {
                "availability": availability,
                "reason": reason,
                "retry_after_s": _parse_retry_after_seconds(text),
                "limit_detected": True,
            }

    if normalized_status == "completed":
        return {
            "availability": "available",
            "reason": "ok",
            "retry_after_s": None,
            "limit_detected": False,
        }
    if normalized_status == "cancelled":
        return {
            "availability": "degraded",
            "reason": "cancelled",
            "retry_after_s": None,
            "limit_detected": False,
        }
    if normalized_status in {"failed", "incomplete"}:
        return {
            "availability": "degraded",
            "reason": normalized_status,
            "retry_after_s": None,
            "limit_detected": False,
        }
    return {
        "availability": "unknown",
        "reason": normalized_status or "unknown",
        "retry_after_s": None,
        "limit_detected": False,
    }


def record_provider_outcome(work_dir: str | Path, provider: str, *, status: str, reply: str) -> Path:
    path = provider_state_path(work_dir, provider)
    payload = load_provider_state(work_dir, provider)
    if not payload:
        payload = {
            "provider": str(provider or "").strip().lower(),
            "created_at": _now_iso(),
            "consecutive_failures": 0,
        }

    classification = classify_provider_outcome(status, reply)
    availability = classification["availability"]
    if availability == "available":
        payload["consecutive_failures"] = 0
        payload["last_success_at"] = _now_iso()
    elif availability in {"degraded", "limited"}:
        payload["consecutive_failures"] = int(payload.get("consecutive_failures") or 0) + 1

    excerpt = str(reply or "").strip()
    if len(excerpt) > 2000:
        excerpt = excerpt[:2000] + "\n...[truncated]"

    payload.update(
        {
            "availability": availability,
            "reason": classification["reason"],
            "retry_after_s": classification["retry_after_s"],
            "limit_detected": classification["limit_detected"],
            "last_status": (status or "").strip().lower() or "completed",
            "last_reply_excerpt": excerpt,
            "updated_at": _now_iso(),
        }
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
