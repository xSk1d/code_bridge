# Coordination Loop

For non-trivial work, follow this loop:

1. Write a short plan with numbered steps.
2. Choose exactly one primary owner for the current step.
3. Use `ask` to assign the step.
4. Use `pend` to read the worker result when needed.
5. Decide one of three outcomes:
   - assign another step
   - request a fix
   - report final status to the user

Default ownership:
- Claude: implementation, bug fixes, tests
- Codex: review, hard refactors, architecture/risk checks

When updating the user, include:
- current owner
- current status
- next step
