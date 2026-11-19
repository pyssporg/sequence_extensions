# seq-ext-gui

Local web GUI for the [`sequence_extensions`](../README.md)
flow engine. Point it at a workflow module, import a `flow-plan/2` JSON plan
(or build one from the module), press **Evaluate** to see the dependency
graph, edit parameters and run options, then press **Execute** and watch the
run log stream in. The plan imports and exports as one JSON document and is
the only runner configuration.

Offline operation, subprocess isolation, and the process split are owned by the
breakdown: [why every job runs in a subprocess](breakdown/02-architecture/gui-application/why-every-job-runs-in-a-subprocess.md)
and [how the GUI is split into processes](breakdown/02-architecture/gui-application/how-the-gui-is-split-into-processes.md).

## Install (development)

The GUI ships in the same distribution as the engine, behind the `gui` extra.
The tests live in `tests/gui/`.

```bash
./setup.sh                   # .venv at the repo root, both packages editable
source .venv/bin/activate
pytest tests/gui
ruff check src tests examples   # one root config governs both packages
```

`setup.sh` creates the repo-root `.venv` with `python3.11` and runs
`pip install -e ".[dev,gui]"`.

## Run

```bash
source .venv/bin/activate
seq-ext-gui --project-root examples/imaginary_flow
# open http://127.0.0.1:8765
```

Pick `flows.py` and its `plan.json` in the left panel's file tree (expand folders
as needed; clicking the JSON imports it), press **Evaluate**, click a node, edit
a parameter or policy that the flow leaves unset, press **Execute**. A flow with required root inputs needs its plan
imported first; Evaluate alone cannot invent those values. Use **Export plan**
(in the graph toolbar) to download the current document as `plan.json`.

Options: `--host`, `--port`, `--project-root`; `SEQ_EXT_GUI_PROJECT_ROOT` is the
environment fallback. The **Project root** field switches directories without a
restart; a running job must finish first.

## What it can and cannot change

Root inputs and unbound node parameters can be edited in the plan; values the
flow binds explicitly always win and are shown read-only. Per-node policy edits
go into `plan.nodes[].policy` and reach the engine as
`RunOptions.node_policies`; edits target one occurrence by identity
(`name #instance`). The override semantics are owned by
[how overrides reach the engine](breakdown/02-architecture/gui-application/how-overrides-reach-the-engine.md)
and [override an input for one node occurrence](breakdown/01-product/planning/override-an-input-for-one-node-occurrence.md).

Run options (`max_workers`, `summary`, `fixed_clock`, run-level
`retries`/`retry_delay_seconds`/`timeout`) are bound directly to the plan's
`options`; the log directory stays per run and is not part of the document.
Flow selection is external: the node list chooses the root node and is never
written into the plan.

See [`docs/gui-architecture.md`](gui-architecture.md) for the wire contract and
the subprocess protocol.

## Breakdown

The repository's product breakdown lives at
[`docs/breakdown/`](breakdown/README.md): current state in its layers, plus the
open improvements. This page is the GUI front door;
[`docs/gui-architecture.md`](gui-architecture.md) is the derived implementation
narrative.

## Layout

The module roles and static files are owned by
[which files make up the package](breakdown/03-implementation/gui-application/which-files-make-up-the-package.md).
