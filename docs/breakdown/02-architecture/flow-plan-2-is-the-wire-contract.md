---
id: INFO-049
type: info
title: Flow-plan/2 is the wire contract
summary: Engine owns the schema; the only contract between the engine and GUI import packages, validated by the GUI
date: 2026-11-19
status: current
---

# Flow-plan/2 is the wire contract

The engine owns the `flow-plan/2` schema; it is the only contract that crosses from `sequence_extensions` to `seq_ext_gui`.

- **Owner:** the engine ships the normative schema at `src/sequence_extensions/schemas/flow-plan-2.schema.json` and exposes `flow.plan_schema()`.
- **Sole contract:** the schema is the only contract across the two import packages; the headless run API applies the shared marker gate, and code crosses through the engine's public symbols (`INFO-047`).
- **Consumer:** the GUI loads the schema from the installed engine and validates plan documents against it (`INFO-048`).
- **No mirror:** the GUI never re-declares the document model; its `editable` and `note` annotations are stripped before export or execution (`INFO-048`).
