---
id: INFO-042
type: info
title: How to run the GUI locally
summary: One command from the repo root, one URL, choose the project root
date: 2026-11-19
status: current
---

# How to run the GUI locally

Activate the repo-root `.venv`, run `seq-ext-gui --project-root examples/flow_runner`, open `http://127.0.0.1:8765`, then choose `flows.py` and `plan.json`.

- **Install:** `pip install -e ".[dev,gui]"` and `source .venv/bin/activate` from the repo root; the `seq-ext-gui` script ships in the one distribution.
- **Run:** `seq-ext-gui --project-root examples/flow_runner`; the examples sit at the repo root now.
- **URL:** `http://127.0.0.1:8765` by default; `--host` and `--port` change it (`INFO-039`).
- **Root:** the **Project root** field opens another directory; a running job must finish first (`CP-044`).
- **Select:** expand directories in the project file tree, then pick `flows.py` and `plan.json`; clicking the JSON imports it and selects the flow the plan was built from, and Evaluate fills the graph.
- **Inspect:** click a node to edit an unbound parameter, press Execute, and read the streamed log.
