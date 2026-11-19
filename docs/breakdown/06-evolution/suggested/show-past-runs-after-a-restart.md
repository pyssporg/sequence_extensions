---
id: IMP-035
type: imp
title: Show past runs after a restart
summary: List earlier jobs from their on-disk directories
date: 2026-11-12
status: suggested
---

# Show past runs after a restart

- **Question:** Should the UI list completed jobs created before the current server process?
- **Evidence:** job records live in memory only; a restart leaves their directories on disk but unreachable from the UI (`INFO-044`).
- **Change:** load job summaries from `.seq_ext_gui/jobs/*` at startup and list them with status and log links.
- **Risk:** stale or half-written results; job ids must come from the directory name, never from client input.
- **Acceptance:** after a restart, a completed run from before the restart is listed with its status and its log.
