---
id: INFO-038
type: info
title: How the worker is invoked
summary: argv request and result files, exit codes, working directory
date: 2026-11-12
status: current
---

# How the worker is invoked

The worker runs once as `python -m seq_ext_gui.worker <request.json> <result.json>`.

- **Input:** one `WorkerRequest` file; `mode` selects `plan` or `execute`.
- **Directory:** the worker passes the flow file's parent as `cwd` to the headless run; the request has no separate `cwd` field.
- **Result:** it always writes the result file, including a handled flow error with `ok=false`.
- **Exit:** 0 for a handled result, non-zero for a worker crash.
- **Output:** stdout and stderr stay silent except a short traceback on crash.
