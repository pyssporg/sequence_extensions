# Imaginary prepare → simulate → post-process flow

A tiny three-stage flow used as a GUI example:

| Node | What it does |
| --- | --- |
| `prepare_data` | Read `data/raw_measurements.csv`, drop bad rows, write `build/examples/imaginary-flow/prepared.json`. |
| `simulate` | Apply a first-order lag model; `gain` and `damping` are editable node parameters. |
| `postprocess` | Compare prediction to measurement, write `build/examples/imaginary-flow/report.json`, return the verdict. |

`pipeline` submits the three nodes in order, so the graph in the GUI is the
chain `prepare_data → simulate → postprocess`.

## Run it in the GUI

```bash
seq-ext-gui --project-root repos/sequence_extensions/examples/imaginary_flow
```

Pick `flows.py`, press **Evaluate**, select `pipeline`, then edit `gain`,
`damping`, or `threshold` on the nodes and press **Execute**. `build/` is
gitignored scratch output.

## Run it from the CLI

```bash
cd repos/sequence_extensions/examples/imaginary_flow
flow-runner plan.json --module flows --flow pipeline --log build/examples/imaginary-flow/logs
```

Import `plan.json` in the GUI when you want the committed defaults as a
starting point.
