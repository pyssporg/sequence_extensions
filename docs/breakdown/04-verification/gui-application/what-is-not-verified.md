---
id: TEST-004
type: test
title: What is not verified
summary: Browser automation, opaque values, nested composites
date: 2026-11-12
status: current
---

# What is not verified

Five areas have no automated proof: the browser path, opaque values, nested composites, long runs, and non-Linux hosts.

- **Browser:** no automated browser test runs in CI; the evaluate-edit-execute walkthrough is manual (`IMP-030`).
- **Opaque values:** non-JSON values are read-only and cannot round-trip through an edit (`IMP-033`).
- **Nested composites:** fan-out inside a node body is absent from the plan (`IMP-031`).
- **Long runs:** no soak test covers a long-running job.
- **Platforms:** CI runs Ubuntu only; no Windows or macOS check exists.
