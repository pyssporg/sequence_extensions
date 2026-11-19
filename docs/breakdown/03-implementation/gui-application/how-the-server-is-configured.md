---
id: INFO-039
type: info
title: How the server is configured
summary: CLI flags, environment fallback, and timeouts
date: 2026-11-12
status: current
---

# How the server is configured

`seq-ext-gui` takes three flags, falls back to an environment variable, and starts uvicorn with two timeouts.

- **Flags:** `--host`, `--port`, `--project-root`.
- **Defaults:** `127.0.0.1` and port `8765`.
- **Root:** `SEQ_EXT_GUI_PROJECT_ROOT`, else the current directory; a non-directory is a parser error.
- **Switch:** `PUT /api/root` accepts an absolute directory and re-points browsing and new jobs (`CP-044`).
- **Timeouts:** `create_app` defaults to 120 s for evaluate and 600 s per execute job.
- **Server:** `cli.py` calls `uvicorn.run(create_app(root), host=..., port=...)`.
