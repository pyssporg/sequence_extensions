---
id: IMP-030
type: imp
title: Automate the browser smoke test
summary: Run the evaluate-edit-execute walkthrough in CI
date: 2026-11-12
status: suggested
---

# Automate the browser smoke test

- **Question:** Can the browser smoke test run in CI instead of by hand?
- **Evidence:** the evaluate-edit-execute walkthrough is manual and no automated browser check exists (`TEST-004`).
- **Change:** add an automated CI browser check of evaluate, edit, and execute.
- **Risk:** a headless browser adds CI time, a new dependency, and flakiness.
- **Acceptance:** CI fails on a broken render or stream without manual steps.
