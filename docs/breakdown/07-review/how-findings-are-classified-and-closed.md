---
id: INFO-046
type: info
title: How findings are classified and closed
summary: Blocker routes to the owning layer; closed when checks pass
date: 2026-11-12
status: current
---

# How findings are classified and closed

A finding is one defect with evidence; it routes to the layer owning the defective fact and closes when that fact and the checks are green.

- **Blocker:** contradictory state presented as current, a failing check or test, or a silent override. Commit stops until fixed.
- **Warning:** stale, duplicated, or misrouted fact, missing leaf sync, broken citation, or budget creep. Fix before commit, but it does not block other changes.
- **Note:** wording, summary drift, or shape suggestion. Fix when the node is next touched.
- **Route:** the finding's home is the layer owning the defective fact; `07-review/` holds criteria, never an open finding or claim (`INFO-045`).
- **Closure:** owning leaf updated and `pb check --strict` plus `pb node-size --strict` green; a code change also passes `pytest` and `ruff` (`INFO-045`).
