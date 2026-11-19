---
id: IMP-037
type: imp
title: Collapse the GUI adapter onto a headless engine run API
summary: engine.py re-derives load, select, plan, apply, execute and result projection that flow_runner also implements
date: 2026-11-19
status: suggested
---

# Collapse the GUI adapter onto a headless engine run API

The engine has no importable headless run path, so the GUI worker re-derives one beside the CLI.

- **Question:** Should load-by-path, flow selection, schema gate, planning, override application, execution, and result projection live once in the engine and be called by both frontends?
- **Evidence:** `src/seq_ext_gui/engine.py` selects the flow and builds "available flows" messages (`engine.py:212-232`) where `flow_runner/__init__.py:151-161` does the same; the schema gate exists three times (`engine.py:238-241`, `flow_runner/__init__.py:78-82`, `_planning/document.py:449-452`); result projection differs (`engine.py:577-596` returns run metadata the CLI drops at `flow_runner/__init__.py:178-197`). The CLI imports a dotted module, so file-path loading exists only GUI-side (`engine.py:160-209`).
- **Change:** add one public headless entry point in the engine that takes a module path, working directory, plan edits, and run options, and returns a serializable result plus run metadata; make `flow-runner` and the GUI worker thin adapters over it. Remove the GUI's duplicate selection, gate, and projection logic.
- **Risk:** user-visible error strings and auto-selection wording change; the CLI currently drops run metadata, so its output shape must be preserved unless deliberately versioned; the worker's `chdir` becomes a parameter, which changes process-global state only if a caller ignores it.
- **Acceptance:** one engine function performs the whole headless unit; `flow-runner` and the GUI worker contain no flow-selection or schema-gate logic of their own; both suites pass; `flow-plan/2` remains the only wire contract.
