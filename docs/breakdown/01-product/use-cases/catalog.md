---
id: INFO-010
type: info
title: Use cases
summary: The use-case catalog — engine CP-016..CP-030 and GUI CP-036..CP-044 under use-cases/; CP-031..CP-035 under planning/
date: 2026-10-14
status: current
---

# Use cases

Each leaf is a capability concretizing `INFO-001`, with a scenario, acceptance, and evidence from the test suite.

- **Engine — `use-cases/`** — `CP-016`..`CP-030`: authoring in Python, concurrency and its bound, DAG ordering, retry and timeout, audit, parameters outside code, embedding, the shell path, byte-stable logs, composite nodes.
- **GUI — `use-cases/`** — `CP-036`..`CP-044`: browse and load a plan, pick the target function, see the graph first, edit inputs and parameters, run and follow the log, cancel, read a failure, export the plan, switch project root.
- **Planning — `planning/`** — `CP-031`..`CP-035` live there: see a flow before it runs, its settable inputs, a one-occurrence override, an override's effect, a plan diff.
