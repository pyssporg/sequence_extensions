# 01-product/planning — Planning Use Cases

The planning journeys — see, tune, and diff a flow plan before anything runs.

## Ask

"What must a user be able to do with a plan before executing it?" — see the graph (`CP-031`), extract the settable inputs (`CP-032`), override one occurrence (`CP-033`), see the override's effect (`CP-034`), diff two plans (`CP-035`).

## When to Read

- Before changing plan documents, overrides, or the plan views.
- When deciding whether a preview belongs to planning or to a run.

## Boundary

- Holds needs only.
- Run-time journeys stay in the parent layer, `01-product/use-cases/`; the plan document's shape and the override route are `02-architecture/` (`INFO-031`, `INFO-047`).

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **CP-031** [See a flow before it runs](see-a-flow-before-it-runs.md) — The complete pre-execution task graph, fan-out width, and parameter values, as one plan document; nothing executed, no log written
- **CP-032** [Extract what a flow can be tuned with](extract-what-a-flow-can-be-tuned-with.md) — A stable input manifest — every settable input of the flow and its nodes, which are required, what each defaults to
- **CP-033** [Override an input for one node occurrence](override-an-input-for-one-node-occurrence.md) — One edited plan document targets one occurrence by identity, or every occurrence of a kind by name; explicit values written in code keep winning
- **CP-034** [See an override's effect before the run](see-an-override-s-effect-before-the-run.md) — A before/after view — which nodes an override reaches and what each receives — from re-planning and comparing the plan documents
- **CP-035** [Diff two flow plans](diff-two-flow-plans.md) — A plain-data diff of two plan documents — added, removed, or re-wired nodes and changed defaults; identical plans compare equal
<!-- pb:index:end -->
