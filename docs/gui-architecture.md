# Architecture and wire contract

Current-state facts live in the repository breakdown at `docs/breakdown/`; this
document is derived implementation narrative.

The GUI is a thin, offline, local presentation layer around the
`sequence_extensions` flow engine. The process split, subprocess isolation, path
confinement, and the one-way engine border are owned by
[how the GUI is split into processes](breakdown/02-architecture/gui-application/how-the-gui-is-split-into-processes.md),
[why every job runs in a subprocess](breakdown/02-architecture/gui-application/why-every-job-runs-in-a-subprocess.md),
[how project paths are confined](breakdown/02-architecture/gui-application/how-project-paths-are-confined.md),
and [how the GUI stays decoupled from the engine](breakdown/02-architecture/gui-application/how-the-gui-stays-decoupled-from-the-engine.md).
Explicit code bindings are not overridable; the override route and its
precedence are owned by [how overrides reach the engine](breakdown/02-architecture/gui-application/how-overrides-reach-the-engine.md)
and [override an input for one node occurrence](breakdown/01-product/planning/override-an-input-for-one-node-occurrence.md).

## Wire contract

The only run configuration is the engine's `flow-plan/2` JSON document. The GUI
does not mirror that document as models. `schema.py` validates plans against the
engine's published JSON Schema (draft 2020-12,
`src/sequence_extensions/schemas/flow-plan-2.schema.json`), and the plan travels as
a plain dict.

- Plan document — `schema`, `parameters`, `nodes`, `edges`, `options`. There is
  no `root`; flow selection is external.
- `Param` — `name`, `type`, `required`, `default`, `value`, plus the GUI-only
  annotations `editable` and `note`. Node — `id`, `name`, `kind`, `path`,
  `instance`, `policy`, `params`; edge — `from`/`to`; policy — `retries`,
  `retry_delay_seconds`, `timeout`.
- Options — the six document options with concrete values taken from the plan
  document, never re-declared locally: `max_workers`, `summary`, `fixed_clock`,
  `retries`, `retry_delay_seconds`, `timeout`.
- `to_document()` strips `editable`/`note` and returns the pure engine document
  for export/execute. Annotations are never schema-validated.
- `JobRequest` — `flow_file`, optional `flow_name`, optional `plan` (a raw
  imported or edited `flow-plan/2` document). `WorkerRequest` adds `mode` and
  `log_dir`; `WorkerResult` carries `flow_name`, `available_flows`, `plan`,
  `run`, `warnings`, `error`, and timings.

## Worker protocol

Invocation (the engine resolves relative paths against the flow file's
directory; there is no separate `cwd` field):

```
python -m seq_ext_gui.worker <request.json> <result.json>
```

`request.json` is a `contracts.WorkerRequest`; `result.json` is a
`contracts.WorkerResult`. The worker always writes a result file, exits 0 on a
handled flow error (`ok=false`) and non-zero only for catastrophic failures.
Nothing else is written to stdout/stderr except a short traceback on crash.

`log_dir` is an absolute per-job directory chosen by `jobs.py`. `engine.execute`
passes it as `log=` to `run_flow`; `jobs.py` tails the single `*.jsonl` file for
SSE.

## engine.py

`seq_ext_gui.engine` is a thin adapter over the public headless API
`sequence_extensions.flow_runner.headless` (`load_flow_module`, `select_flow`,
`require_plan_document`, `run_flow`, `HeadlessRun`). It keeps only GUI policy:
worker request/result shapes, root-seed decode, seed-edit override, wire-plan
annotation, JSON-Schema validation, and error/timing mapping.

```python
def plan(request: WorkerRequest) -> WorkerResult
def discover(request: WorkerRequest) -> WorkerResult
def execute(request: WorkerRequest) -> WorkerResult
```

`discover` loads the flow module with `load_flow_module` and returns node cards
from `find_nodes`; it executes no node body.

`plan` builds the wire plan without executing user node bodies:

1. If `request.plan` is present, `require_plan_document` requires
   `flow-plan/2`; a complete document is also JSON-Schema validated.
2. `load_flow_module` imports the flow file by path and `select_flow` picks
   `request.flow_name` or the only node. Ambiguity returns `ok=false` with
   `available_flows` from the shared selection error.
3. `_root_values` decodes the seed's root `parameters` with `decode_value`; a
   missing required or unknown root parameter is `ok=false`.
4. `run_flow(..., seed=root_kwargs, cwd=flow_parent, plan_only=True)` returns
   the base `flow-plan/2` document.
5. `_override_from_seed` diffs the seed against that fresh document by exact
   node identity `(name, path, instance)`; seed `options` join the same
   override. `apply_override` produces the edited document. Only values that
   differ from the fresh plan are emitted. A seed node without identity (legacy
   plan) or with an identity the fresh plan no longer contains is skipped with
   a warning; there is no name-wide fallback.
6. Return the annotated plan dict with the editability heuristic below. `editable`/`note`
   come from the freshly generated document (code values); the overlaid values
   are displayed, so an edited parameter that was re-evaluated stays editable.

`execute`:

7. Require `request.plan`; otherwise `EngineError("execute requires a plan")`.
8. `require_plan_document` then `validate_plan` gate the document; `to_document`
   strips the wire annotations.
9. `run_flow(..., document=document, log=request.log_dir, cwd=flow_parent)` loads,
   selects, and executes. Do not re-plan: the plan document is authoritative.
10. On success the run projection is `HeadlessRun.to_dict()["run"]`; on a flow
    exception `exc.run` is projected the same way and the error, type, and
    traceback are reported. Never swallow. `run.result` passes through
    `jsonable` in the shared projection.

`run_flow`'s `cwd` is process-global and restored on exit. The GUI always uses
the flow file's parent, so the request has no separate `cwd`.

### Parameter editability rule (documented heuristic)

- Root parameters: editable.
- Node parameter with `required=true` and a non-null value: read-only,
  `note="set by flow code"`.
- Node parameter with `required=false` and `value == default`: editable.
- Node parameter whose value differs from its default: read-only with
  `note="possibly set by flow code"`.
- `kind="gather"` nodes: no parameters.
- Edits are keyed by node identity `(name, path, instance)`, so an edit hits
  exactly one occurrence. Name-wide overrides remain an engine capability but
  the GUI does not emit them. A stale or missing identity is skipped with a
  warning rather than applied name-wide.

## HTTP API (all JSON, same origin)

| Method | Path | Body / result |
|---|---|---|
| GET | `/api/health` | `HealthResponse` |
| PUT | `/api/root` | `{"path": str}` -> `HealthResponse`; switches the active root |
| GET | `/api/tree?path=` | `TreeResponse`; dirs plus `*.py`/`*.json` files, hidden entries and `__pycache__`/`.git`/`.venv`/`runs`/`.seq_ext_gui` skipped |
| GET | `/api/file?path=` | `FileContent`; read `.py`/`.json` under the project root |
| POST | `/api/evaluate` | `JobRequest` -> `WorkerResult` (synchronous, spawned worker) |
| POST | `/api/discover` | `JobRequest` -> `WorkerResult`; node cards, no plan and no execution |
| POST | `/api/execute` | `JobRequest` -> `{"job_id": str}` |
| GET | `/api/jobs/{id}` | `JobStatus` |
| GET | `/api/jobs/{id}/events` | SSE: `status` | `log` | `done` events |
| POST | `/api/jobs/{id}/cancel` | `JobStatus`; kills the process group |

There is no project-file write endpoint: the GUI does not save project files. All
`path`/`flow_file` values are resolved against the configured project root;
anything outside it is rejected with HTTP 400; `ValueError` maps to 400 and an
unknown job id to 404. `project_root` comes from `seq-ext-gui --project-root`,
else `SEQ_EXT_GUI_PROJECT_ROOT`, else the current directory. `PUT /api/root`
replaces it at runtime; browsing and new jobs follow the active root, while a
running job keeps the root it started with.

SSE event shapes:

```
event: status
data: {"state": "running"}          (also queued/succeeded/failed/cancelled)

event: log
data: {"record": {...}}             (one parsed JSONL run-log record)

event: done
data: {"state": "succeeded", "result": {...WorkerResult}}
```

The stream closes after `done`. Late subscribers get the current status first.

## Frontend

The two-panel layout, file tree, toolbar, graph, parameter widgets, and
run-option placement are owned by
[what the browser UI consists of](breakdown/03-implementation/gui-application/what-the-browser-ui-consists-of.md).

The GUI-only payload is `{flow_file, flow_name, plan}`: Evaluate sends the
current plan (if any) as the seed, Execute sends it and requires one, and Export
downloads `planDocument(state.plan)` as `plan.json`. Import requires
`schema === "flow-plan/2"` and re-runs Evaluate so the engine validates and
refreshes the document against the selected workflow. Export and execution
strip the GUI-only `editable`/`note` annotations (`planDocument()` in the
browser; `to_document()` in the Python worker).
