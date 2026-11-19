---
id: INFO-037
type: info
title: What the HTTP API exposes
summary: Endpoints, payloads, and error mapping
date: 2026-11-12
status: current
---

# What the HTTP API exposes

The API is a same-origin JSON surface plus one SSE stream; evaluate is synchronous and execute is a background job.

- **Health:** `GET /api/health` returns version and project root.
- **Files:** `GET /api/tree` and `GET /api/file` list and read `.py`/`.json`; there is no write endpoint.
- **Evaluate:** `POST /api/evaluate` runs a plan-mode worker and returns its `WorkerResult` directly.
- **Execute:** `POST /api/execute` returns `{"job_id": ...}` immediately.
- **Jobs:** `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, `POST /api/jobs/{id}/cancel`.
- **Errors:** `ValueError` maps to 400; an unknown job id maps to 404.
- **Static:** `/` serves `index.html`, `/static` serves the assets, both no-cache.
