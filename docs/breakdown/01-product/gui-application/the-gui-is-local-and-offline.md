---
id: REQ-002
type: requirement
title: The GUI is local and offline
summary: Localhost only, no remote assets, no telemetry
date: 2026-11-12
status: current
---

# The GUI is local and offline

The server binds to localhost, serves every asset itself, sends no telemetry, and starts from one explicit command.

- **Promise:** flow code and parameters never leave the machine, and the browser loads no remote asset.
- **Why it matters:** flow definitions are project-internal, and an air-gapped operator still gets the full UI.
- **Violated by:** a non-local bind default, a CDN link, or any outbound call from the page.
- **Notice:** the start command names the project root and the address to open (`INFO-042`), and the page makes no external request.
