---
id: INFO-030
type: info
title: Why every job runs in a subprocess
summary: Fresh imports, crash isolation, and a process group to kill
date: 2026-11-12
status: current
---

# Why every job runs in a subprocess

A fresh worker process per job keeps saved edits visible and keeps crashes away from the API.

- **Fresh imports:** a new process re-imports the flow file; a saved edit cannot be hidden by stale `sys.modules`.
- **Name collisions:** flow files with the same stem get distinct synthetic module names.
- **Crash isolation:** an import error or hard crash kills only the worker; the API keeps serving.
- **Killable:** the worker runs in its own session, so cancel and timeout kill the whole group.
- **Contract:** each job is one request file in and one result file out (`INFO-038`).
- **Cost:** every job pays interpreter and import startup; acceptable for a local GUI.
