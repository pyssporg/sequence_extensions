---
id: INFO-027
type: info
title: What is out of scope
summary: No scheduling, no flow-code editing, no multi-user service
date: 2026-11-12
status: current
---

# What is out of scope

The GUI is a local single-user preview and run tool; scheduling, code editing, history, and multi-user service stay out.

- **Local single user:** binds `127.0.0.1:8765` by default; no accounts, roles, or auth (`REQ-002`, `INFO-039`).
- **Editable surface:** the `flow-plan/2` JSON document is edited in memory and imported or exported; `.py` files are read-only and the GUI writes no project files (`INFO-037`).
- **No node-code editing:** the author edits the `@node` module outside the GUI (`INFO-026`).
- **No scheduling or HPC:** each run starts from the browser; batch, cron, and HPC submission stay with `flow-runner` (`INFO-028`).
- **No run-history database:** each job writes its own directory under `.seq_ext_gui/jobs`; no cross-run query (`INFO-044`).
- **No plotting:** the graph shows node dependencies only, not result data (`INFO-035`).
- **No cross-platform promise:** process-group cancel is POSIX; Windows and macOS stay unverified (`INFO-030`).
