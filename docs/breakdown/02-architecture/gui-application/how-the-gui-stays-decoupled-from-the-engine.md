---
id: INFO-047
type: info
title: How the GUI stays decoupled from the engine
summary: One repo, one distribution with a GUI extra, one-way dependency on the public headless run API plus the plan schema
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
- **Interface:** the public headless run API — `HeadlessRun`, `load_flow_module`, `select_flow`, `require_plan_document`, `run_flow` — plus `find_nodes`, `apply_override`, `RunOptions`, `NodeFunction`, `PLAN_SCHEMA`, `jsonable`, and `NodePolicy`/`plan_schema` for schema defaults, with the published `flow-plan/2` JSON Schema (`INFO-049`).
- **Boundary:** `run_flow` owns loading, selection, the schema gate, planning and overrides, execution, and run projection; the GUI keeps root-seed validation, override warnings, wire annotation, and schema-artifact validation.
- **Direction:** the engine imports nothing from `seq_ext_gui`; the direction is enforced, not conventional.
