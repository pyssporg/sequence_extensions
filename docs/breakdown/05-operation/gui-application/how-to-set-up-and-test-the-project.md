---
id: INFO-043
type: info
title: How to set up and test the project
summary: From the repo root, one .venv, install .[dev,gui], pytest and pytest tests/gui, ruff
date: 2026-11-19
status: current
---

# How to set up and test the project

From the repo root, create one `.venv`, install `.[dev,gui]`, then run the engine suite, the GUI suite, and ruff.

- **Venv:** `python3.11 -m venv .venv` creates the environment inside the repo root.
- **Install:** `pip install -e ".[dev,gui]"` installs the engine, the GUI, and the dev tools from the one distribution.
- **Engine:** the engine is part of this repo; no sibling checkout and no path outside it (`INFO-041`).
- **Test:** `pytest` at the repo root runs `tests/` for the engine; `pytest tests/gui` runs the GUI suite.
- **Lint:** `ruff check .` from the repo root covers both packages.
