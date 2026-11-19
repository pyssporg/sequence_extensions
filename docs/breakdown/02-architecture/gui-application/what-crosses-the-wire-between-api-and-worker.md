---
id: INFO-033
type: info
title: What crosses the wire between API and worker
summary: One contracts module for the process models; the plan crosses as a plain JSON document
date: 2026-11-13
status: current
---

# What crosses the wire between API and worker

`contracts.py` defines every pydantic model that crosses between API and worker; the wire data is JSON files.

- **Single module:** `JobRequest`, `WorkerRequest`, `WorkerResult`, `JobStatus`, and the file payloads live in one module.
- **Plan as a document:** the plan crosses as a plain JSON object; its shape is the engine's `flow-plan/2` schema, checked by `schema.py` (`INFO-048`); no pydantic plan mirror exists.
- **Request file:** `JobRequest` carries `flow_file`, optional `flow_name`, and the optional `plan` document; `WorkerRequest` adds `mode` and `log_dir`. Absent fields stay absent, and the plan, when present, is authoritative.
- **Result file:** `WorkerResult` carries the plan, the run account, warnings, and any error; `WorkerResult.plan` normalises an incoming plan dict to the schema defaults.
- **Direction:** the API writes a request; the worker writes a result; neither shares memory with the other.
