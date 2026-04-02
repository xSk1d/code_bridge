# Read Provider Reply

Use `pend <provider> [N]` to read the latest reply from another provider.

Rules:
- Use this only when the user asks for the result or when you need the reply to continue.
- Keep the provider name explicit.

Execution:

```bash
pend "$PROVIDER" ${N:-}
```
