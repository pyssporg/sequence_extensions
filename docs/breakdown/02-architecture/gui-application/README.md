# 02-architecture/gui-application — GUI Architecture

How the GUI is organized to meet its requirements — process split, message flow, and the engine border.

## Ask

"How is the GUI organized, and where is its edge with the engine?" — the processes (`INFO-029`), subprocess isolation (`INFO-030`), overrides (`INFO-031`), the live log (`INFO-032`), the API/worker wire (`INFO-033`), path confinement (`INFO-034`), offline layout (`INFO-035`), and engine decoupling (`INFO-047`).

## When to Read

- Before changing a process boundary or the API/worker contract.
- Before touching anything on the engine border.

## Boundary

- Holds the organizing design only.
- Files, endpoints, and flags are `03-implementation/gui-application/`; the proof is `04-verification/gui-application/`.
- Engine-internal architecture stays in the parent layer, `02-architecture/` (`INFO-003`, `INFO-011`).

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-029** [How the GUI is split into processes](how-the-gui-is-split-into-processes.md) — Browser, API, job manager, worker subprocess, engine adapter
- **INFO-030** [Why every job runs in a subprocess](why-every-job-runs-in-a-subprocess.md) — Fresh imports, crash isolation, and a process group to kill
- **INFO-031** [How overrides reach the engine](how-overrides-reach-the-engine.md) — GUI edits the plan document per occurrence; engine semantics live in CP-033 and CP-034
- **INFO-032** [How the browser learns about a running job](how-the-browser-learns-about-a-running-job.md) — Per-job log directory, JSONL tail, SSE events
- **INFO-033** [What crosses the wire between API and worker](what-crosses-the-wire-between-api-and-worker.md) — One contracts module for the process models; the plan crosses as a plain JSON document
- **INFO-034** [How project paths are confined](how-project-paths-are-confined.md) — Every file path resolves inside the project root
- **INFO-035** [How the graph is laid out offline](how-the-graph-is-laid-out-offline.md) — Layered SVG computed in the browser, no CDN
- **INFO-047** [How the GUI stays decoupled from the engine](how-the-gui-stays-decoupled-from-the-engine.md) — One repo, one distribution with a GUI extra, one-way dependency on nine symbols plus the plan schema
<!-- pb:index:end -->
