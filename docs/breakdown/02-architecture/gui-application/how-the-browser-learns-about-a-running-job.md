---
id: INFO-032
type: info
title: How the browser learns about a running job
summary: Per-job log directory, JSONL tail, SSE events
date: 2026-11-12
status: current
---

# How the browser learns about a running job

The browser follows a running job through an SSE stream fed by the job's JSONL run log.

- **Log location:** each job owns `.seq_ext_gui/jobs/<id>/logs` with one `*.jsonl` file.
- **Tail:** the stream loop reads new complete lines every 150 ms.
- **Events:** `status` reports the job state, `log` one parsed record, `done` the final result; `done` closes the stream.
- **Reconnect:** each log event carries an index as its SSE id; `Last-Event-ID` resumes after that index.
- **Live:** records arrive while the run still runs (`REQ-004`).
