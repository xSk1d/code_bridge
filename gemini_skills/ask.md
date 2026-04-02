# Ask AI Provider

Use `ask` to delegate work to another provider from Gemini.

Rules:
- Prefer `ask <provider>` instead of provider-specific wrappers.
- Pass the message via stdin heredoc, not inline CLI arguments.
- Set `CCB_CALLER=gemini`.
- After submitting, report that the task was handed off and stop. Do not poll in the same turn.

Execution:

```bash
CCB_CALLER=gemini ask "$PROVIDER" <<'EOF'
$MESSAGE
EOF
```
