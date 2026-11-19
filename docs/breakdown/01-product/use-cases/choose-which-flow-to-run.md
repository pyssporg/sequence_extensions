---
id: CP-037
type: capability
title: Choose which flow to run
summary: Pick the target when a module defines several node functions
date: 2026-11-12
status: current
---

# Choose which flow to run

When a module holds several flows the operator picks the target from the node list after clicking the module in the project file tree (expanding directories as needed); when exactly one node exists, it is used without a choice. Selection is external to the plan.

- **Request:** "run the flow I mean from this module, or use its only node."
- **Goal:** no doubt about which flow the preview describes.
- **Observable outcome:** a flow selector lists the module's flows; with one node, Evaluate proceeds on its own, and the choice is never written into the plan.
- **Where it fits:** between loading a module (`CP-036`) and previewing it (`CP-038`).
- **Where it strains:** several flows and no selection stop Evaluate with an error that lists the available flows.
