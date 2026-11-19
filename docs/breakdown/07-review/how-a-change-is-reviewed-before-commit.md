---
id: INFO-045
type: info
title: How a change is reviewed before commit
summary: Leaf first, then checks, tests, and a browser pass
date: 2026-11-12
status: current
---

# How a change is reviewed before commit

A change is reviewed before commit by reading its owning leaf, syncing state, then passing the definition and code gates.

- **Leaf first:** read the owning leaf before code and keep it current in the same change; the breakdown wins on disagreement until a decision changes it.
- **Definition gates:** run `pb check --strict` and `pb node-size --strict` from the breakdown root.
- **Code gates:** run `pytest` and `ruff check src tests`; the setup and test procedure owns the commands (`INFO-043`).
- **UI pass:** for a UI change, start the GUI, Evaluate the campaign example, then Execute and read the run log (`INFO-042`).
- **Generated surfaces:** never hand-edit `## Contents` rows or registers; release builds rebuild them with `pb registers`.
