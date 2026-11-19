---
id: IMP-033
type: imp
title: Support non-JSON parameter values
summary: Edit parameters whose values cannot cross the wire today
date: 2026-11-12
status: suggested
---

# Support non-JSON parameter values

- **Question:** Can parameters whose values are not JSON cross the wire and round-trip?
- **Evidence:** opaque values show as read-only, so the operator cannot edit them (`INFO-031`).
- **Change:** add type-aware serialization for common non-JSON values.
- **Risk:** a wrong encoder silently changes a value.
- **Acceptance:** a `Path`, enum, and dataclass parameter round-trip through the UI.
