---
id: INFO-048
type: info
title: How a plan document is validated
summary: schema.py loads the installed engine artifact, caches a draft 2020-12 validator, reports capped path errors
date: 2026-11-19
status: current
---

# How a plan document is validated

`schema.py` validates every `flow-plan/2` document against the engine schema shipped in the installed package; the GUI keeps no pydantic mirror of the plan.

- **Load:** `importlib.resources` reads `sequence_extensions/schemas/flow-plan-2.schema.json` from the installed engine; `sequence_extensions.flow.plan_schema()` is the fallback; both load once per process.
- **Contract:** the schema is the only document model that crosses between packages, so the GUI never re-declares it (`INFO-049`).
- **Validate:** one cached `Draft202012Validator`; `validate_plan` raises `PlanValidationError` with errors sorted by JSON path and capped at five.
- **Partial seeds:** `is_complete_document` requires every top-level `required` key and every `$defs/options` property; an incomplete seed is validated only after the engine re-plans it.
- **Defaults:** `option_defaults` and `policy_defaults` read `RunOptions().resolve("plan")` and `NodePolicy()` in schema property order, filling imported plans.
- **Annotations:** `editable` and `note` are GUI-only dict keys; `to_document()` strips them before export or execution (`INFO-033`).
