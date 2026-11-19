---
id: INFO-029
type: info
title: How the GUI is split into processes
summary: Browser, API, job manager, worker subprocess, engine adapter
date: 2026-11-12
status: current
---

# How the GUI is split into processes

Four boundaries split the GUI: browser, HTTP API, job manager, and worker.

- **Browser:** renders the plan and collects parameter edits; runs no engine code.
- **HTTP API:** serves JSON and SSE; never imports the engine or a user flow module.
- **Job manager:** spawns one worker per job, enforces timeouts, kills the process group on cancel, and tails the run log.
- **Worker:** imports the flow module and the engine, plans or executes, and writes one result file.
- **Engine adapter:** `engine.py` is the only module that imports `sequence_extensions`, inside the worker.
