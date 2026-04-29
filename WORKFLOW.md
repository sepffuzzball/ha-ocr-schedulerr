---
tracker:
  kind: local
  active_states:
    - Ready
    - In Progress
  terminal_states:
    - Done
    - Cancelled
polling:
  interval_ms: 30000
workspace:
  root: ./.agent/workspaces
agent:
  max_concurrent_agents: 3
  max_turns: 20
  max_retry_backoff_ms: 300000
hooks:
  timeout_ms: 60000

---

# Repository Workflow

You are working on a repository task.

## Required behavior

1. Read the task description and acceptance criteria.
2. Inspect the relevant files before editing.
3. Update `.agent/BOARD.md` when task status changes.
4. Make the smallest coherent change that satisfies the task.
5. Add or update tests when appropriate.
6. Update docs when behavior, setup, architecture, or configuration changes.
7. Run relevant validation commands.
8. Record important decisions in `.agent/DECISIONS.md`.
9. Leave a concise handoff note with:
   - Summary
   - Files changed
   - Tests/checks run
   - Remaining risks
   - Next steps
