# 01-product/use-cases — Use Cases

The capability leaves — engine use cases `CP-016`..`CP-030` and GUI use cases `CP-036`..`CP-044` — plus the catalog that groups them.

## Ask

"What must a user be able to do, seen from outside?" — the engine journeys (`CP-016`..`CP-030`), the GUI journeys (`CP-036`..`CP-044`), and the catalog at `INFO-010`.

## When to Read

- Before promising or changing a capability.
- When an integrator asks what must work, for the engine or for the GUI.

## Boundary

- Holds needs only.
- Planning-only journeys (`CP-031`..`CP-035`) are `01-product/planning/`; the delivered design is `02-architecture/`.
- GUI-wide requirements stay in the parent layer, `01-product/gui-application/` (`REQ-001`..`REQ-004`).

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **CP-016** [UC-16 Define a flow in Python](uc-16-define-a-flow-in-python.md) — an engineer authors a campaign as ordinary Python — functions, calls, returns; no schema, no XML
- **CP-017** [UC-17 Run independent tasks concurrently](uc-17-run-independent-tasks-concurrently.md) — independent nodes inside one run execute at the same time; the run returns only once every node has finished
- **CP-018** [UC-18 Order dependent tasks — general DAG](uc-18-order-dependent-tasks-general-dag.md) — nodes may depend on other nodes in any shape, joins and diamonds included; a dependent node receives its dependency's result; cycles are rejected at declaration
- **CP-019** [UC-19 Retry, back off, and bound a task](uc-19-retry-back-off-and-bound-a-task.md) — a flaky node is tried again after a pause; a hanging node is cut off by a per-attempt wall-clock budget
- **CP-020** [UC-20 Audit a run](uc-20-audit-a-run.md) — every run leaves one complete, ordered record — each attempt, each skip, and the run's verdict, readable with plain tools
- **CP-021** [UC-21 Bound the concurrency](uc-21-bound-the-concurrency.md) — concurrent nodes never exceed a limit the caller chooses; a caller may instead supply one shared pool that serves several runs
- **CP-022** [UC-22 Run CPU-bound tasks in parallel](uc-22-run-cpu-bound-tasks-in-parallel.md) — compute-heavy tasks run on several cores of one machine at the same time, without rewriting the campaign or losing its record
- **CP-023** [UC-23 Run flows concurrently in one process](uc-23-run-flows-concurrently-in-one-process.md) — several campaigns run at the same time in one process without interfering with each other
- **CP-024** [UC-24 See what a run did](uc-24-see-what-a-run-did.md) — a completed run read back at a glance — per task the attempts, the statuses, and the time spent, plus the run's verdict — without reading raw records
- **CP-025** [UC-25 Verify two runs executed identically](uc-25-verify-two-runs-executed-identically.md) — same code and same inputs must execute the same — every node, every attempt, same outcomes — with completion order, clock readings, and worker identity never counting as differences
- **CP-026** [UC-26 Set a run's parameters outside the code](uc-26-set-a-runs-parameters-outside-the-code.md) — run options, per-node policy, and root inputs live in one flow-plan/2 JSON document; explicit parameter values keep winning, plan policy overrides decorator policy, and the document launches the run without a code change
- **CP-027** [UC-27 Embed the engine in a host application](uc-27-embed-the-engine-in-a-host-application.md) — host application calls execute_flow with per-call RunOptions, reads the returned Run — no service, no global configuration, no dependencies
- **CP-028** [UC-28 Start runs from a shell or pipeline](uc-28-start-runs-from-a-shell-or-pipeline.md) — make, CI, cron, and batch scripts start flows through flow-runner, select the root with --flow, branch on exit codes, keep the run log as the artifact
- **CP-029** [UC-29 Keep a run log byte-stable for reference storage](uc-29-keep-a-run-log-byte-stable-for-reference-storage.md) — reference mode: fixed_clock pins run id, timing, worker, and record order — identical runs produce byte-identical log files
- **CP-030** [UC-30 Compose nodes — a node inside a node](uc-30-compose-nodes-a-node-inside-a-node.md) — a reusable node tree runs as a step in a larger node tree — one run, one log, future-first fan-out, and composite policy for the subtree
- **CP-036** [Find and load a flow and its plan](find-and-load-a-flow-and-its-config.md) — Browse a project, pick a flow module, import or build its plan
- **CP-037** [Choose which flow to run](choose-which-flow-to-run.md) — Pick the target when a module defines several node functions
- **CP-038** [See the graph before anything runs](see-the-graph-before-anything-runs.md) — Nodes, edges, fan-out, parameters, and policy before execution
- **CP-039** [Edit an input the flow leaves settable](edit-an-input-the-flow-leaves-settable.md) — Change root inputs and unbound node parameters, then see the new plan
- **CP-040** [Execute a flow and watch it run](execute-a-flow-and-watch-it-run.md) — Start a run with edits applied and follow its log live
- **CP-041** [Stop a run](stop-a-run.md) — Cancel a running flow without restarting the server
- **CP-042** [Understand why a run failed](understand-why-a-run-failed.md) — See the failing node path, the error, and the verdict
- **CP-043** [Save a plan edit](save-a-config-edit.md) — Export the edited plan as a plan.json download
- **CP-044** [Switch the project root](switch-the-project-root.md) — Open another project without restarting the server
- **INFO-010** [Use cases](catalog.md) — The use-case catalog — engine CP-016..CP-030 and GUI CP-036..CP-044 under use-cases/; CP-031..CP-035 under planning/
<!-- pb:index:end -->
