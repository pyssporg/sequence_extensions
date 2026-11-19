---
id: CP-036
type: capability
title: Find and load a flow and its plan
summary: Browse a project, pick a flow module, import or build its plan
date: 2026-11-12
status: current
---

# Find and load a flow and its plan

The operator browses the project, opens one flow module, and imports or builds its `flow-plan/2` document; the selection area names both.

- **Request:** "show me this project's flow modules and plans, and let me load one module with its plan."
- **Goal:** preview the real project files, not a copy.
- **Observable outcome:** the browser lists folders plus flow modules and plan documents; the selection area names the chosen module and flow, and browsing stays inside the configured project root (`INFO-034`).
- **Where it fits:** the first step of every session, and the input to the preview (`CP-038`).
- **Where it strains:** a plan written for a different module still imports; the mismatch shows only at Evaluate as an unknown flow or parameter.
