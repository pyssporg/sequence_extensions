# Architecture and wire contract

Current-state facts live in the repository breakdown at `docs/breakdown/`; this
document is derived implementation narrative.

The GUI (`src/seq_ext_gui/`, shipped by the same distribution behind the `gui`
extra, tested in `tests/gui/`) is a thin, offline, local presentation layer
around the `sequence_extensions` flow engine. It never imports user flow code
into the web process.

```
browser (vanilla JS, SVG graph)
   |  JSON + SSE
FastAPI app (app.py, files.py, jobs.py)
   |  one subprocess per evaluate/execute, request/result JSON files
worker.py -> engine.py -> sequence_extensions API
```

## Hard invariants

1. `app.py`, `jobs.py`, `files.py` never import `sequence_extensions` or a user
   flow module. Only `engine.py` does, and only inside the worker process.
2. `engine.py` uses only `plan_document`, `apply_override`, `execute_plan`,
   `RunOptions`, `NodePolicy`, `jsonable`, and `find_nodes`. No engine logic is
   copied.
3. Every evaluate/execute gets a fresh worker process and a fresh job directory.
4. Values the flow binds explicitly are not overridable and are shown read-only.
5. No CDN, no network assets, no build step in `static/`.

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

Invocation (the worker changes into the flow file's directory; there is no
separate `cwd`):

```
python -m seq_ext_gui.worker <request.json> <result.json>
```

`request.json` is a `contracts.WorkerRequest`; `result.json` is a
`contracts.WorkerResult`. The worker always writes a result file, exits 0 on a
handled flow error (`ok=false`) and non-zero only for catastrophic failures.
Nothing else is written to stdout/stderr except a short traceback on crash.

`log_dir` is an absolute per-job directory chosen by `jobs.py`. `engine.execute`
passes it as `log=` to `execute_plan`; `jobs.py` tails the single `*.jsonl`
file for SSE.

## engine.py

```python
def plan(request: WorkerRequest) -> WorkerResult
def execute(request: WorkerRequest) -> WorkerResult
```

`plan` builds the wire plan without executing user node bodies:

1. Import the flow file by absolute path (verified loader: package-aware branch,
   `sys.modules` registration before `exec_module`, parent on `sys.path`); the
   worker has already changed into the file's directory.
2. `find_nodes(module)`; select `request.flow_name` or the only node. Ambiguity
   returns `ok=false` with `available_flows` populated.
3. If `request.plan` is present, require `schema == "flow-plan/2"`; decode its
   root `parameters` with `decode_value`, then build `RunOptions` from its
   `options`.
4. A missing required root parameter is `ok=false` naming the parameters.
5. `doc = plan_document(fn, options=run_options, **root_kwargs)`.
6. If a seed plan was given, preserve its edits: match each seed node by exact
   identity `(name, path, instance)` and call
   `apply_override(doc, {parameters, nodes[]})` with `path`/`instance` on every
   node entry. Only values that differ from the fresh plan are emitted. A seed
   node without identity (legacy plan) or with an identity the fresh plan no
   longer contains is skipped with a warning; there is no name-wide fallback.
   Seed `options` are not applied twice — they were already used to plan.
7. Return a `WirePlan` with the editability heuristic below. `editable`/`note`
   come from the freshly generated document (code values); the overlaid values
   are displayed, so an edited parameter that was re-evaluated stays editable.
8. No runner-config object and no separate `cwd`; the working directory is
   always the flow file's parent.

`execute`:

9. Require `request.plan`; otherwise `EngineError("execute requires a plan")`.
10. Import and select the flow, then
    `execute_plan(fn, request.plan, log=request.log_dir)`. Do not re-plan: the
    plan document is authoritative.
11. Return `ok=true` with `run` and the executed plan as a `WirePlan`; on a flow
    exception, use `exc.run` when present and map it to `RunResult`; never
    swallow. `run.result` is passed through `jsonable`.

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
| GET | `/api/tree?path=` | `TreeResponse`; dirs plus `*.py`/`*.json` files, hidden and `__pycache__`/`.git`/`.venv`/`runs` skipped |
| GET | `/api/file?path=` | `FileContent`; read `.py`/`.json` under the project root |
| POST | `/api/evaluate` | `JobRequest` -> `WorkerResult` (synchronous, spawned worker) |
| POST | `/api/execute` | `JobRequest` -> `{"job_id": str}` |
| GET | `/api/jobs/{id}` | `JobStatus` |
| GET | `/api/jobs/{id}/events` | SSE: `status` | `log` | `done` events |
| POST | `/api/jobs/{id}/cancel` | `JobStatus`; kills the process group |

There is no project-file write endpoint: the GUI does not save project files. All
`path`/`flow_file` values are resolved against the configured project root;
anything outside it is rejected with HTTP 400. `project_root` comes from
`seq-ext-gui --project-root`, else `SEQ_EXT_GUI_PROJECT_ROOT`, else the current
directory. `PUT /api/root` replaces it at runtime; browsing and new jobs follow
the active root, while a running job keeps the root it started with.

SSE event shapes:

```
event: status
data: {"state": "running"}          (also queued/cancelled)

event: log
data: {"record": {...}}             (one parsed JSONL run-log record)

event: done
data: {"state": "succeeded", "result": {...WorkerResult}}
```

The stream closes after `done`. Late subscribers get the current status first.

## Frontend

Two vertical panels, per the product request:

- Left: project-root field with **Open**, a nested project file tree (`.py`/`.json`)
  where directories expand in place (children fetched lazily per directory and
  cached) and the selected flow file stays marked, and **Evaluate**. **Import plan**, **Export plan** and the plan status sit in the
  graph toolbar, with the import file input.
- Right: SVG DAG (oriented top-to-bottom, layered by longest path), node click
  selects it and opens the parameter and policy editor in a side column,
  **Execute** button, live run log, result banner. The side column also holds
  the run-option fields; they show while the flow root (or nothing) is selected
  and are hidden when a concrete node takes over the column.

Clicking a `.json` file in the tree imports it; clicking a `.py` file selects
the workflow. Expanding a directory fetches only that level. The single
**Open**/**Refresh** button beside the root field opens a typed root or, when
the path is unchanged, re-fetches the root and every expanded directory while
preserving the expanded set. Import requires `schema === "flow-plan/2"` and runs Evaluate so
the engine validates and refreshes the document against the selected workflow;
with no flow selected the UI shows a clear message. Export downloads
`planDocument(state.plan)` as `plan.json`.

Root inputs and node parameters mutate `state.plan.parameters[]` and the
selected `state.plan.nodes[].params[]` directly; the policy editor mutates the
selected `state.plan.nodes[].policy`; option fields mutate
`state.plan.options`. Repeated nodes are shown and edited as `name #instance`,
so one edit never touches a sibling occurrence. Any edit marks the plan dirty
and re-enables Evaluate. `buildPayload()` returns
`{flow_file, flow_name, plan}`; Evaluate sends the current plan (if any) as the
seed, Execute sends it and requires one.

Editable parameter widgets derive from `Param.type`: `bool` checkbox, `int`/
`float` number input, `Path`/`str` text input, `list`/`dict` JSON textarea.
Read-only params render disabled with their `note` as a tooltip. The displayed
root-node label is the selected or evaluated flow name, not a plan field.
