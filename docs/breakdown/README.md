# Product Breakdown — sequence_extensions and the GUI

Current-state record for the one distribution in this repo, `sequence-extensions-flow`: the engine library — sequence helpers, graph futures, the flow engine — installed plainly, plus the GUI application that previews and runs flows locally, installed with the `gui` extra. Both import packages live under `src/`; the tests split between `tests/` and `tests/gui/`. For authors and agents.

## The Eight Layers

- `00-intent/` — why does it exist, who is it for? (`gui-application/`: the GUI's intent)
- `01-product/` — what is delivered, out of scope? (`use-cases/`: `CP-016`..`CP-030` engine, `CP-036`..`CP-044` GUI; `planning/`: `CP-031`..`CP-035`; `gui-application/`: `REQ-`)
- `02-architecture/` — how are deliverables, evidence, and work organized?
- `03-implementation/` — with what concrete assets is it realized?
- `04-verification/` — how do we know it satisfies the requirements?
- `05-operation/` — how do authors run, maintain, release?
- `06-evolution/` — what work is open: the suggested → selected → implemented IMP funnel, `investigations/`, `plans/`
- `07-review/` — how are the definition and its implementation scrutinized?
- the decision archive (`docs/archive/archive.zip`) — dated history, read via `pb archive`, never browsed

## Boundary Rule

A document's home is the layer whose question it answers; information flows downward only.
- Current state: layer leaves, present tense. History: the archive, dated records. Tracking: the IMP's `status:`, never a leaf.
- Review is the exception: it reads the whole stack and routes findings back; it owns no claim.
- This file indexes current state only.

## Find a Fact

- Current state: this file, then the owning layer index, then the one leaf whose summary matches; stop there.
- History: the archive record-by-record via `pb archive read`; never browse the stream. Candidates: `06-evolution/suggested/` and `selected/`.
- Cite nodes by stable ID, never by path.

## Route an Edit

- Current-state fact: update the owning layer leaf.
- Dated choice: a decision record via `pb archive add`.
- Candidate change: an IMP in `06-evolution/suggested/`; once selected, `selected/` plus its plan.
- One fact has exactly one home; defer cross-layer material by ID.
- Never hand-edit generated registers or index `## Contents` lists.

## Excludes

- Implementation detail, durable rationale, `docs/API.md`, and `docs/references/`: runtime-coupled, outside this tree.
