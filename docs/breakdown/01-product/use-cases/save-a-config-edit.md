---
id: CP-043
type: capability
title: Save a plan edit
summary: Export the edited plan as a plan.json download
date: 2026-11-12
status: current
---

# Save a plan edit

The operator edits the plan in the UI and exports it as a `plan.json` download on an explicit action; the imported document is validated at Evaluate.

- **Request:** "keep this plan change in a file I can commit or share."
- **Goal:** the downloaded document matches the plan the UI shows.
- **Observable outcome:** Export downloads the current `flow-plan/2` document as `plan.json`; the GUI writes no project file and nothing is downloaded until Export is pressed.
- **Where it fits:** after a run or a plan edit (`CP-042`); the exported document can be re-imported and feeds the next Evaluate (`CP-038`).
- **Where it strains:** Export strips the editability annotations; a hand-edited JSON file is checked only when it is imported or evaluated.
