---
id: TEST-003
type: test
title: What runs in CI
summary: One tests workflow, engine and GUI jobs, Python 3.11 and 3.12, split coverage
date: 2026-11-19
status: current
---

# What runs in CI

One tests workflow runs two jobs — engine and GUI — on Python 3.11 and 3.12 from a single checkout.

- **Workflow:** `.github/workflows/tests.yml` triggers on every push to `main` and every pull request.
- **Jobs:** an engine job and a GUI job, one per import package.
- **Python:** both jobs matrix over 3.11 and 3.12, with fail-fast off so every combination finishes.
- **Checkout:** Actions checks out the one repo; no sibling engine clone.
- **Install:** both jobs install `.[dev,gui]` editable, with pip caching.
- **Engine coverage:** the engine job measures `sequence_extensions` and enforces the repo `fail_under = 90` gate.
- **GUI coverage:** the GUI job measures `seq_ext_gui` with no `fail_under` gate.
- **Checks:** ruff and pytest run per job (`INFO-041`).
