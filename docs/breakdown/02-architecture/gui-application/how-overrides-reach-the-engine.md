---
id: INFO-031
type: info
title: How overrides reach the engine
summary: GUI edits the plan document per occurrence; engine semantics live in CP-033 and CP-034
date: 2026-11-19
status: current
---

# How overrides reach the engine

The GUI edits the plan document; `apply_override` carries each edit to the engine, whose matching and precedence rules live in the capability leaves.

- **Edit:** a node edit carries `path` and `instance`, so it targets one occurrence.
- **Apply:** `apply_override` writes the value into the plan document; `execute_plan` rebuilds the node registry from it.
- **Policy:** the document's `nodes[].policy` reaches the engine as `RunOptions.node_policies`.
- **Preview:** the GUI re-plans with the edit and compares the two documents before the run (`CP-034`).
- **Semantics:** identity or name matching, and code binding beating a document value, follow `CP-033`.
- **Stale identity:** an identity absent from the plan is skipped with a warning (`CP-033`).
