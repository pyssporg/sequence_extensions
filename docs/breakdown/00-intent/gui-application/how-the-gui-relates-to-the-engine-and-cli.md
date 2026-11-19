---
id: INFO-028
type: info
title: How the GUI relates to the engine and CLI
summary: Same engine API as the CLI; the CLI stays the batch path
date: 2026-11-12
status: current
---

# How the GUI relates to the engine and CLI

The GUI shares the engine API with the CLI; the CLI stays the batch path, GUI adds preview and plan editing.

- **Same API:** the GUI and the CLI both call the engine's headless run API (`run_flow`); the GUI adds `apply_override` and its own wire policy, and copies no engine logic (`INFO-047`).
- **Shared inputs:** both paths read one flow module and one `flow-plan/2` JSON plan.
- **CLI role:** `flow-runner PLAN.json --module MODULE [--flow NAME]` runs a prepared plan as the batch path, with no preview or edit step.
- **GUI adds:** graph preview, plan import/export, per-run plan edits, and a run log that streams while the run runs (`REQ-004`).
- **Isolation:** every GUI evaluate or execute runs in a fresh subprocess; the web process never imports flow code (`INFO-030`).
- **Limitation:** a value the flow binds explicitly stays read-only; the GUI cannot override code (`INFO-031`, `REQ-001`).
