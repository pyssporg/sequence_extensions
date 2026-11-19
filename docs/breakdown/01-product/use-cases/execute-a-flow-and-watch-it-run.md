---
id: CP-040
type: capability
title: Execute a flow and watch it run
summary: Start a run with edits applied and follow its log live
date: 2026-11-12
status: current
---

# Execute a flow and watch it run

The operator executes the previewed flow with the current edits, watches records arrive, and reads the final verdict.

- **Request:** "run it as previewed and show me what happens."
- **Goal:** a run that uses exactly the edits that were previewed.
- **Observable outcome:** records appear in the log as attempts finish; the verdict names status, duration, result, error, failed nodes, and the log location.
- **Where it fits:** closes the edit loop (`CP-039`); leads to stop (`CP-041`) and failure reading (`CP-042`).
- **Where it strains:** the log shows finished attempts only, so a node still running has no line yet (`REQ-004`).
