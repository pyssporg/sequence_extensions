# 01-product/gui-application — GUI Product Requirements

The guarantees the GUI owes its operator — what never happens silently, and how a run reaches the screen.

## Ask

"What must the GUI guarantee the user observes?" — planning runs no submitted node body (`REQ-003`), code-bound values stay read-only with every limitation warned (`REQ-001`), the tool stays local and offline (`REQ-002`), and the run log streams while the run runs (`REQ-004`).

## When to Read

- Before promising or changing a GUI behaviour.
- When deciding whether a limitation needs a visible warning.

## Boundary

- Holds requirements only.
- The user-facing journeys are `01-product/use-cases/`; the design that satisfies them is `02-architecture/gui-application/`.
- Engine-wide needs stay in the parent layer, `01-product/use-cases/` (`CP-016`..`CP-030`).

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **REQ-001** [No override applies silently](no-override-applies-silently.md) — Code-bound values are read-only, and every limitation is warned
- **REQ-002** [The GUI is local and offline](the-gui-is-local-and-offline.md) — Localhost only, no remote assets, no telemetry
- **REQ-003** [Evaluate runs no submitted node body](evaluate-runs-no-submitted-node-body.md) — Planning executes orchestration only; node bodies wait for Execute
- **REQ-004** [The run log streams while the run runs](the-run-log-streams-while-the-run-runs.md) — One record per finished attempt, visible before the run ends
<!-- pb:index:end -->
