# 00-intent/gui-application — GUI Intent

Why a GUI exists beside the engine and the CLI, who runs it, and what it refuses to do.

## Ask

"Why does a GUI exist, and who does it serve?" — the local-view need (`INFO-025`), the two audiences (`INFO-026`), the refusals (`INFO-027`), and the division of labour with the CLI (`INFO-028`).

## When to Read

- Before proposing a GUI capability the intent does not already admit.
- When judging whether a request belongs to the GUI or to the engine.

## Boundary

- Holds intent only.
- What the GUI must deliver is `01-product/gui-application/`; how it is built is `02-architecture/gui-application/`.
- The engine's own vision and non-goals stay in the parent layer, `00-intent/` (`INFO-001`); this folder defers to it and never restates it.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-025** [Why the GUI exists](why-the-gui-exists.md) — A local view of a flow and its inputs before a run
- **INFO-026** [Who uses the GUI](who-uses-the-gui.md) — Flow authors build; flow operators run and tune existing flows
- **INFO-027** [What is out of scope](what-is-out-of-scope.md) — No scheduling, no flow-code editing, no multi-user service
- **INFO-028** [How the GUI relates to the engine and CLI](how-the-gui-relates-to-the-engine-and-cli.md) — Same engine API as the CLI; the CLI stays the batch path
<!-- pb:index:end -->
