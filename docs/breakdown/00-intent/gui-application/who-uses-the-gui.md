---
id: INFO-026
type: info
title: Who uses the GUI
summary: Flow authors build; flow operators run and tune existing flows
date: 2026-11-12
status: current
---

# Who uses the GUI

The GUI serves a flow author who writes the `@node` module and a flow operator who runs a prepared flow.

- **Flow author needs:** the node graph, flow names, and the run log to debug a module that fails (`INFO-025`).
- **Flow author does not need:** a node-body editor; `@node` code stays in the author's editor (`INFO-027`).
- **Flow operator needs:** flow selection, plan import or export, root and unbound node parameters, node policy, run options, then Execute (`INFO-031`).
- **Flow operator does not need:** Python editing, scheduling, or HPC submission (`INFO-027`).
- **Shared boundary:** both use one local UI with no accounts or roles (`REQ-002`).
