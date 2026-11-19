# 05-operation/gui-application — GUI Operation

How an author starts the GUI, sets up the project, and finds what a run left behind.

## Ask

"How does an author run the GUI and inspect its artifacts?" — one command and one URL (`INFO-042`), the setup and test path (`INFO-043`), and where job artifacts go (`INFO-044`).

## When to Read

- When starting the GUI or setting up the project.
- When looking for a job's request, result, stderr, or run log.

## Boundary

- Holds procedure only.
- Engine install, run, and HPC recipes stay in the parent layer, `05-operation/`.
- Release steps are not here: they are the repository's build tooling, outside this tree.

## Contents

<!-- pb:index:start -->
<!-- GENERATED FILE — do not edit. Regenerate with pb-registers. -->
- **INFO-042** [How to run the GUI locally](how-to-run-the-gui-locally.md) — One command from the repo root, one URL, choose the project root
- **INFO-043** [How to set up and test the project](how-to-set-up-and-test-the-project.md) — From the repo root, one .venv, install .[dev,gui], pytest and pytest tests/gui, ruff
- **INFO-044** [Where job artifacts go](where-job-artifacts-go.md) — Per-job request, result, stderr, and run log under the project root
<!-- pb:index:end -->
