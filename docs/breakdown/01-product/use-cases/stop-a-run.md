---
id: CP-041
type: capability
title: Stop a run
summary: Cancel a running flow without restarting the server
date: 2026-11-12
status: current
---

# Stop a run

The operator cancels an active run; the run is marked cancelled and the server keeps serving.

- **Request:** "stop this run now."
- **Goal:** end a long or mistaken run without restarting the GUI.
- **Observable outcome:** a Cancel action is offered only during a run; afterwards the run state reads cancelled and the log stays readable.
- **Where it fits:** during a run started from Execute (`CP-040`); a cancelled run leaves the GUI usable (`INFO-030`).
- **Where it strains:** attempts already finished stay in the log; cancel is not an undo.
