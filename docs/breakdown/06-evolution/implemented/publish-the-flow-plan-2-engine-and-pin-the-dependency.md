---
id: IMP-036
type: imp
title: Publish the flow-plan/2 engine and pin the dependency
summary: Implemented. The engine ships flow-plan/2 and flow.plan_schema(); the GUI now ships in the same distribution, so no dependency pin remains
date: 2026-11-13
status: implemented
---

# Publish the flow-plan/2 engine and pin the dependency

Implemented: the engine publishes the schema with its package, and the GUI ships in the same distribution, so no version pin or workspace requirement remains.

- **Question:** How does the GUI reach an engine revision that supports `flow-plan/2`?
- **Evidence:** the GUI needed `execute_plan` and `flow-plan/2`, which existed only in a local engine commit; upstream `main` was behind it and PyPI had no `sequence-extensions-flow` package (`INFO-041`, `TEST-003`).
- **Change:** the engine publishes `flow-plan/2` with the `sequence-extensions-flow` package and exposes the schema as `flow.plan_schema()`; the GUI first shipped as a `>=3.1.0` workspace requirement, then joined the same distribution, so the git-tag pin, the version requirement, and the separate checkout are gone (`INFO-047`).
- **Risk:** a missing or too-old engine can no longer be selected independently of the GUI; one version now serves both.
- **Acceptance:** a clean `pip install -e ".[dev,gui]"` gives a GUI that resolves the engine schema from the same distribution, and CI passes (`TEST-003`).
