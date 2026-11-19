---
id: IMP-034
type: imp
title: Add a plan diff view
summary: Compare two evaluations of the same flow
date: 2026-11-12
status: suggested
---

# Add a plan diff view

- **Question:** Can two evaluations of the same flow be compared?
- **Evidence:** two evaluations cannot be compared because no diff view exists.
- **Change:** add a plan diff view.
- **Risk:** node identity changes between runs, so matching by name can pair the wrong nodes.
- **Acceptance:** added, removed, and parameter-changed nodes are listed between two plans.
