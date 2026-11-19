# 03-implementation/gui-application — GUI Implementation

The concrete assets — modules, endpoints, flags, worker protocol, plan validation, and the engine wiring.

## Ask

"With what concrete assets is the GUI realized?" — module roles (`INFO-036`), the HTTP surface (`INFO-037`), worker invocation (`INFO-038`), server configuration (`INFO-039`), the browser UI (`INFO-040`), the engine dependency (`INFO-041`), and plan validation (`INFO-048`).

## When to Read

- Before touching a module, endpoint, flag, or dependency declaration.
- When checking how a plan document is validated against the engine artifact.

## Boundary

- Holds assets only.
- The design they realize is `02-architecture/gui-application/`; how to run them is `05-operation/gui-application/`.
- The engine's own asset map stays in the parent layer, `03-implementation/`.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-036** [Which files make up the package](which-files-make-up-the-package.md) — Module roles under src/seq_ext_gui, tests under tests/gui, docs/gui.md, shared root config
- **INFO-037** [What the HTTP API exposes](what-the-http-api-exposes.md) — Endpoints, payloads, and error mapping
- **INFO-038** [How the worker is invoked](how-the-worker-is-invoked.md) — argv request and result files, exit codes, working directory
- **INFO-039** [How the server is configured](how-the-server-is-configured.md) — CLI flags, environment fallback, and timeouts
- **INFO-040** [What the browser UI consists of](what-the-browser-ui-consists-of.md) — Four static files, plan import/export panel, SVG graph, no build step
- **INFO-041** [How the engine dependency is wired](how-the-engine-dependency-is-wired.md) — Editable install of the one distribution with the gui extra, schema from the installed engine, no version pin
- **INFO-048** [How a plan document is validated](how-a-plan-document-is-validated.md) — schema.py loads the installed engine artifact, caches a draft 2020-12 validator, reports capped path errors
<!-- pb:index:end -->
