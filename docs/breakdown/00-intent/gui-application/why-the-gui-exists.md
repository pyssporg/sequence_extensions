---
id: INFO-025
type: info
title: Why the GUI exists
summary: A local view of a flow and its inputs before a run
date: 2026-11-12
status: current
---

# Why the GUI exists

The GUI exists so one user can inspect a flow and tune editable inputs before a run, without editing code.

- **Gap:** `flow-runner PLAN.json --module MODULE` runs a prepared plan as a batch job with no graph view and no parameter editor.
- **Users:** flow author and flow operator, who differ in intent, not permission (`INFO-026`).
- **Outcome:** the user sees the dependency graph, edits editable inputs, then executes and reads the streamed log (`INFO-028`).
- **Local:** one user on localhost; no account, remote asset, or telemetry (`REQ-002`).
- **Non-goals:** not a scheduler, flow-code editor, plotting tool, or service (`INFO-027`).
