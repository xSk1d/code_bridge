from __future__ import annotations

from provider_roles import delegated_role_prefix, startup_bootstrap


def test_gemini_role_text_marks_manager_behavior() -> None:
    text = delegated_role_prefix("gemini")
    lowered = text.lower()
    assert "coordinator" in lowered
    assert "default to delegation first" in lowered
    assert "delegate most coding and test-writing to claude" in lowered
    assert "use codex for review" in lowered
    assert "plan -> assign owner -> wait for result" in lowered
    assert "agents.md" in lowered
    assert "claude.md" in lowered
    assert "team roles" in lowered


def test_claude_role_text_marks_implementation_behavior() -> None:
    text = delegated_role_prefix("claude")
    assert "primary implementation worker" in text
    assert "coding, debugging, and writing tests" in text
    assert "STATUS:" in text
    assert "CHANGED_FILES:" in text


def test_startup_bootstrap_exists_for_main_roles() -> None:
    assert "main coordinator" in startup_bootstrap("gemini")
    assert "primary coder" in startup_bootstrap("claude")
    assert "reviewer and heavy-lift engineer" in startup_bootstrap("codex")
    assert "Pick one owner for each step" in startup_bootstrap("gemini")
    assert "Follow repository markdown instructions" in startup_bootstrap("gemini")
    assert "Do not start work" in startup_bootstrap("gemini")
    assert "teammates" in startup_bootstrap("claude")
