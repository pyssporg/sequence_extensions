# 07-review — Review

How a change is scrutinized — the pre-commit pass and how a finding is classified and closed.

## Ask

"How is a change reviewed, and how does a finding close?" — leaf first, then checks, tests, and a browser pass (`INFO-045`); a blocker routes to the owning layer and closes only when checks pass (`INFO-046`).

## When to Read

- Before committing a change.
- When filing or closing a review finding.

## Boundary

- Holds procedure only, never a claim of its own.
- Review reads the whole stack and routes each finding to the layer owning the defective fact; the corrected fact belongs in that layer (e.g. `02-architecture/`), not here.
- The engine's and the GUI's current state stay in their owning layers.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-045** [How a change is reviewed before commit](how-a-change-is-reviewed-before-commit.md) — Leaf first, then checks, tests, and a browser pass
- **INFO-046** [How findings are classified and closed](how-findings-are-classified-and-closed.md) — Blocker routes to the owning layer; closed when checks pass
<!-- pb:index:end -->
