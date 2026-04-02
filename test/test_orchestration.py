from __future__ import annotations

import json
from pathlib import Path

from orchestration import (
    record_task_completion,
    record_task_spawn,
    record_task_submission,
    render_completion_event,
)


def test_task_record_lifecycle(tmp_path: Path) -> None:
    cfg_dir = tmp_path / ".ccb"
    cfg_dir.mkdir()

    path = record_task_submission(
        tmp_path,
        task_id="task-1",
        provider="claude",
        caller="gemini",
        message="Implement feature X",
        log_file="/tmp/task.log",
        status_file="/tmp/task.status",
        caller_pane_id="%1",
        caller_terminal="tmux",
    )
    assert path.exists()

    record_task_spawn(tmp_path, task_id="task-1", pid=1234)
    record_task_completion(
        tmp_path,
        task_id="task-1",
        provider="claude",
        status="completed",
        reply="STATUS: done",
        output_file="/tmp/out.txt",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["task_id"] == "task-1"
    assert payload["provider"] == "claude"
    assert payload["caller"] == "gemini"
    assert payload["state"] == "completed"
    assert payload["pid"] == 1234
    assert payload["completion_status"] == "completed"
    assert payload["output_file"] == "/tmp/out.txt"


def test_render_completion_event_includes_task_fields() -> None:
    message = render_completion_event(
        "Claude",
        "task-1",
        "STATUS: done",
        output_file="/tmp/out.txt",
        status="completed",
        task_file="/repo/.ccb/tasks/task-1.json",
    )

    assert "CCB_ORCH_EVENT: task_complete" in message
    assert "CCB_TASK_ID: task-1" in message
    assert "CCB_TASK_PROVIDER: Claude" in message
    assert "CCB_TASK_STATUS: completed" in message
    assert "CCB_TASK_FILE: /repo/.ccb/tasks/task-1.json" in message
    assert "CCB_OUTPUT_FILE: /tmp/out.txt" in message
