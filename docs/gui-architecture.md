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
def discover(request: WorkerRequest) -> WorkerResult
def execute(request: WorkerRequest) -> WorkerResult
```

`discover` returns node cards from the module signature and executes no node
body. `plan` builds the wire plan without executing user node bodies:

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
7. Return the annotated plan dict with the editability heuristic below. `editable`/`note`
   come from the freshly generated document (code values); the overlaid values
   are displayed, so an edited parameter that was re-evaluated stays editable.
8. No runner-config object and no separate `cwd`; the working directory is
   always the flow file's parent.

`execute`:

9. Require `request.plan`; otherwise `EngineError("execute requires a plan")`.
10. Import and select the flow, then
    `execute_plan(fn, request.plan, log=request.log_dir)`. Do not re-plan: the
    plan document is authoritative.
11. Return `ok=true` with `run` and the annotated executed-plan dict; on a flow
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
