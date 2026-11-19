---
id: REQ-004
type: requirement
title: The run log streams while the run runs
summary: One record per finished attempt, visible before the run ends
date: 2026-11-12
status: current
---

# The run log streams while the run runs

Each finished attempt appears in the log while the run is still going, not only at the end.

- **Promise:** records arrive one per finished attempt, visible before the final verdict.
- **Why it matters:** a long run shows progress, and a hang is distinguishable from slow work.
- **Violated by:** a log that appears only at the end, or records buffered until the job completes.
- **Notice:** the log panel fills as attempts finish, and the status line leaves running only after the last record (`CP-040`).
