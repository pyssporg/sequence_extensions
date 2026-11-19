---
id: CP-039
type: capability
title: Edit an input the flow leaves settable
summary: Change root inputs and unbound node parameters, then see the new plan
date: 2026-11-12
status: current
---

# Edit an input the flow leaves settable

The operator changes root inputs and node parameters the flow leaves unset, then re-evaluates to see the new plan.

- **Request:** "let me try other values without touching the flow code."
- **Goal:** tune a run from the preview.
- **Observable outcome:** the edited value shows in the parameter editor, only the selected occurrence changes, and the plan is marked stale until the next Evaluate reflects it.
- **Where it fits:** on an evaluated plan (`CP-038`), before Execute (`CP-040`).
- **Where it strains:** a read-only value stays disabled and gives its reason, so an edit the flow binds never applies (`REQ-001`).
