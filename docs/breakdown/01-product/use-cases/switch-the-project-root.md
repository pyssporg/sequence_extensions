---
id: CP-044
type: capability
title: Switch the project root
summary: Open another project without restarting the server
date: 2026-11-12
status: current
---

# Switch the project root

The operator points the GUI at another directory and works there without restarting the server.

- **Request:** "open the other project directory here."
- **Goal:** move between projects in one session instead of restarting the server.
- **Observable outcome:** the file tree, the health line, and new job directories follow the chosen directory; the old flow and plan are cleared.
- **Where it fits:** before finding a flow (`CP-036`), and only while no run is active.
- **Where it strains:** a running job keeps the root it started with, so the switch waits for it to finish.
