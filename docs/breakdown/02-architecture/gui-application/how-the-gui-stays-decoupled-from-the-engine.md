---
id: INFO-047
type: info
title: How the GUI stays decoupled from the engine
summary: One repo, one distribution with a GUI extra, one-way dependency on nine symbols plus the plan schema
date: 2026-11-19
status: current
---

# How the GUI stays decoupled from the engine

One repository ships one distribution, and the dependency runs one way: the GUI imports the engine, never the reverse.

- **One distribution:** `sequence-extensions-flow` sits at the repo root; the base install declares runtime dependencies `[]`, and the GUI sits behind the `gui` extra.
- **Install:** `pip install "sequence-extensions-flow[gui]"` adds the GUI; the base install stays standard-library only.
- **Import packages:** `src/sequence_extensions` is the engine and `src/seq_ext_gui` is the GUI, both under the one package tree.
- **GUI deps:** the `gui` extra adds `fastapi`, `uvicorn[standard]`, and `jsonschema`.
- **One version:** `sequence_extensions.__version__` is the single source; `seq_ext_gui` re-exports it, so no separate GUI distribution exists.
- **Interface:** nine symbols from `sequence_extensions.flow` and `sequence_extensions.flow_runner`, plus the published `flow-plan/2` JSON Schema (`INFO-049`).
- **Named operations:** `plan_document`, `apply_override`, `execute_plan`, and `find_nodes`; option types `RunOptions` and `NodePolicy`; `jsonable` converts results.
- **Direction:** the engine imports nothing from `seq_ext_gui`; the direction is enforced, not conventional.
