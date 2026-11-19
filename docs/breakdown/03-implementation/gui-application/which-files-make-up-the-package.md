---
id: INFO-036
type: info
title: Which files make up the package
summary: Module roles under src/seq_ext_gui, tests under tests/gui, docs/gui.md, shared root config
date: 2026-11-19
status: current
---

# Which files make up the package

The GUI is one import package at `src/seq_ext_gui`, with its tests at `tests/gui`, its examples, and its docs beside the engine.

- **Core:** `contracts` holds the wire models and plan-dict helpers, `schema` validates plans against the engine schema, `engine` adapts the flow engine, `worker` is the subprocess entry point.
- **Server:** `app` defines the endpoints, `jobs` supervises workers, `files` confines browsing, `cli` starts uvicorn.
- **Static:** `index.html`, `app.js`, `graph.js`, `styles.css`; no build output.
- **Tests:** `tests/gui` holds one module per concern — API, engine, files, jobs, schema, static, worker — plus `conftest.py` fixtures.
- **Examples:** `examples/imaginary_flow` ships a browsable flow and plan for the GUI.
- **Docs:** `docs/gui.md` for users and `docs/gui-architecture.md` for the wire contract.
- **Packaging:** one root `pyproject.toml` declares both packages and the `gui` extra; the root ruff and pytest configuration serves both suites.
