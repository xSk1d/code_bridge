from __future__ import annotations

from gaskd_protocol import wrap_gemini_prompt


def test_wrap_gemini_prompt_injects_gemini_skills() -> None:
    wrapped = wrap_gemini_prompt("Delegate this to Claude.", "req-123")

    assert "Gemini Coordinator Role" in wrapped
    assert "CCB_CALLER=gemini ask" in wrapped
    assert "pend \"$PROVIDER\"" in wrapped
    assert "CCB_DONE: req-123" in wrapped
