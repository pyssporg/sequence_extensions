---
id: INFO-041
type: info
title: How the engine dependency is wired
summary: Editable install of the one distribution with the gui extra, schema from the installed engine, no version pin
date: 2026-11-19
status: current
---

# How the engine dependency is wired

The GUI ships in the same distribution as the engine, so it installs with the `gui` extra and needs no version requirement.

- **Development:** from the repo root, `pip install -e ".[dev,gui]"` installs the engine, the GUI, and the dev tools into one `.venv`.
- **Extra:** the `gui` extra carries `fastapi`, `uvicorn[standard]`, and `jsonschema`; the base install keeps runtime dependencies `[]`.
- **No pin:** no separate GUI distribution and no version requirement exist; both packages share `sequence_extensions.__version__`.
- **Schema source:** the installed engine ships `src/sequence_extensions/schemas/flow-plan-2.schema.json` and exposes `flow.plan_schema()` (`INFO-049`).
- **CI:** the tests workflow installs `.[dev,gui]` and runs an engine job and a GUI job (`TEST-003`).
