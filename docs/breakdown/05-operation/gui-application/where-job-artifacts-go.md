---
id: INFO-044
type: info
title: Where job artifacts go
summary: Per-job request, result, stderr, and run log under the project root
date: 2026-11-12
status: current
---

# Where job artifacts go

Each job writes one directory under `<project_root>/.seq_ext_gui/jobs/<id>/` and leaves flow outputs where the flow writes them.

- **Layout:** `request.json`, `result.json`, `stderr.log`, and `logs/` sit in that directory.
- **Log:** `logs/` holds the single `*.jsonl` run log that SSE tails (`INFO-032`).
- **Evaluate:** plan-mode jobs use `eval-<hex>` ids; execute jobs use a plain hex id.
- **Ignored:** `.seq_ext_gui/` is gitignored.
- **Flow output:** node files such as `_out/` go where the flow writes them, not into the job directory.
