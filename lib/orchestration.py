from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from session_utils import resolve_project_config_dir


_STATUS_LABELS = {
    "completed": "Completed",
    "cancelled": "Cancelled",
    "failed": "Failed",
    "incomplete": "Incomplete",
}

_STATUS_MARKERS = {
    "completed": "[CCB_TASK_COMPLETED]",
    "cancelled": "[CCB_TASK_CANCELLED]",
    "failed": "[CCB_TASK_FAILED]",
    "incomplete": "[CCB_TASK_INCOMPLETE]",
}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def task_dir(work_dir: str | Path) -> Path:
    base = resolve_project_config_dir(Path(work_dir))
    return base / "tasks"


def task_file_path(work_dir: str | Path, task_id: str) -> Path:
    return task_dir(work_dir) / f"{task_id}.json"


def load_task_record(work_dir: str | Path, task_id: str) -> dict[str, Any]:
    path = task_file_path(work_dir, task_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def upsert_task_record(work_dir: str | Path, task_id: str, **fields: Any) -> Path:
    path = task_file_path(work_dir, task_id)
    data = load_task_record(work_dir, task_id)
    if not data:
        data = {"task_id": task_id, "created_at": _now_iso()}
    data.update({k: v for k, v in fields.items() if v is not None})
    data["updated_at"] = _now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def record_task_submission(
    work_dir: str | Path,
    *,
    task_id: str,
    provider: str,
    caller: str,
    message: str,
    log_file: str,
    status_file: str,
    caller_pane_id: str = "",
    caller_terminal: str = "",
) -> Path:
    preview = (message or "").strip()
    if len(preview) > 500:
        preview = preview[:500] + "..."
    return upsert_task_record(
        work_dir,
        task_id,
        provider=provider,
        caller=caller,
        state="submitted",
        message_preview=preview,
        log_file=log_file,
        status_file=status_file,
        caller_pane_id=caller_pane_id or "",
        caller_terminal=caller_terminal or "",
    )


def record_task_spawn(work_dir: str | Path, *, task_id: str, pid: int | None) -> Path:
    return upsert_task_record(
        work_dir,
        task_id,
        state="running",
        pid=int(pid) if isinstance(pid, int) else None,
    )


def record_task_completion(
    work_dir: str | Path,
    *,
    task_id: str,
    provider: str,
    status: str,
    reply: str,
    output_file: str | None = None,
) -> Path:
    reply_excerpt = (reply or "").strip()
    if len(reply_excerpt) > 4000:
        reply_excerpt = reply_excerpt[:4000] + "\n...[truncated]"
    return upsert_task_record(
        work_dir,
        task_id,
        provider=provider,
        state="completed",
        completion_status=status,
        output_file=output_file or "",
        reply_excerpt=reply_excerpt,
        completed_at=_now_iso(),
    )


def render_completion_event(
    provider_display: str,
    req_id: str,
    reply_content: str,
    *,
    output_file: str | None,
    status: str,
    task_file: str | None,
) -> str:
    normalized_status = (status or "").strip().lower() or "completed"
    marker = _STATUS_MARKERS.get(normalized_status, _STATUS_MARKERS["completed"])
    status_label = _STATUS_LABELS.get(normalized_status, _STATUS_LABELS["completed"])
    task_file_line = f"CCB_TASK_FILE: {task_file}\n" if task_file else ""
    output_file_line = f"CCB_OUTPUT_FILE: {output_file}\n" if output_file else ""
    result_block = (reply_content or "").strip()
    return (
        f"CCB_REQ_ID: {req_id}\n"
        "CCB_ORCH_EVENT: task_complete\n"
        f"CCB_TASK_ID: {req_id}\n"
        f"CCB_TASK_PROVIDER: {provider_display}\n"
        f"CCB_TASK_STATUS: {normalized_status}\n"
        f"{task_file_line}"
        f"{output_file_line}\n"
        f"{marker}\n"
        f"Provider: {provider_display}\n"
        f"Status: {status_label}\n\n"
        f"Result:\n{result_block}\n"
    )
