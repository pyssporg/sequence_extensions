"""``flow-runner`` — launch a plan file's run from the command line.

    flow-runner PLAN.json --module MODULE [--flow NAME] [--log DIR]
    flow-runner --module MODULE --list

One ``flow-plan/2`` JSON document carries everything the run needs: the root
callable's bound parameters, every node's parameters and effective policy,
the edges, and the run options.  The module is named on the command line and
imported like any other; the root node is external state, selected with
``--flow`` (or auto-selected when the module defines exactly one node).

``PLAN`` is ``-`` for stdin.  ``--log DIR`` overrides the plan's log
location (the plan itself never stores it).  ``--list`` prints the module's
nodes and exits without reading a plan.

Exit codes: ``0`` the run succeeded; ``1`` the run raised; ``2`` usage or
configuration error (bad plan JSON/schema, missing or unknown flow, an
import-time failure, or a plan that does not fit the flow).

Nodes needing non-JSON inputs (open connections, custom objects) belong in a
small ``main.py`` that calls ``execute_flow`` directly — the runner is a
convenience, not a requirement.  A plan file names a module to import, so
treat it as trusted code.  Process pools are constructed in code; the runner
drives thread-mode runs.

This module is the command-line adapter over :mod:`.headless`: it owns only
argument parsing, plan-file reading, output wording, and exit-code mapping.
:mod:`._discovery` holds the node scan.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
import traceback
from pathlib import Path

from sequence_extensions.flow import jsonable

from ._discovery import find_nodes
from .headless import (
    HeadlessRun,
    load_flow_module,
    require_plan_document,
    run_flow,
    select_flow,
)

__all__ = [
    "HeadlessRun",
    "find_nodes",
    "load_flow_module",
    "main",
    "require_plan_document",
    "run_flow",
    "select_flow",
]

#: Exit codes: 0 ok, 1 run failure, 2 usage/config error.
EXIT_OK = 0
EXIT_RUN_ERROR = 1
EXIT_USAGE = 2


# ---------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------- #
def _fail(message: str) -> int:
    print(f"flow-runner: {message}", file=sys.stderr)
    return EXIT_USAGE


def _read_plan(source: Path) -> dict:
    """Load and shape-check a plan JSON document (``-`` reads stdin)."""
    if str(source) == "-":
        text = sys.stdin.read()
        where = "stdin"
    else:
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as e:
            raise ValueError(f"cannot read plan file {source}: {e}") from None
        where = str(source)

    try:
        document = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"{where}: invalid JSON: {e}") from None

    if not isinstance(document, dict):
        raise ValueError(f"{where}: plan must be a JSON object, got {type(document).__name__}")
    try:
        return require_plan_document(document)
    except ValueError as e:
        raise ValueError(f"{where}: {e}") from None


def main(argv: list[str] | None = None) -> int:
    """Run the flow a plan document describes.  Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="flow-runner",
        description="Run a flow from a flow-plan/2 JSON document.",
    )
    parser.add_argument(
        "plan",
        nargs="?",
        type=Path,
        help="path to the plan JSON file ('-' for stdin); not needed with --list",
    )
    parser.add_argument(
        "--module",
        required=True,
        metavar="MODULE",
        help="dotted module name scanned for @node functions",
    )
    parser.add_argument(
        "--flow",
        metavar="NAME",
        help="root node to run (defaults to the module's only node)",
    )
    parser.add_argument(
        "--log",
        type=Path,
        metavar="DIR",
        help="override the plan's log directory",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list the module's nodes and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        try:
            module = load_flow_module(args.module)
            entries = [(name, _first_doc_line(fn)) for name, fn in find_nodes(module).items()]
        except (ImportError, OSError, ValueError) as e:
            return _fail(str(e))
        print(f"flows in {args.module}:")
        for node_name, summary in entries:
            print(f"  {node_name}" + (f"  — {summary}" if summary else ""))
        if not entries:
            print("  (none found)")
        return EXIT_OK

    if args.plan is None:
        return _fail("no plan given — pass PLAN.json (or - for stdin)")

    try:
        document = _read_plan(args.plan)
    except ValueError as e:
        return _fail(str(e))

    try:
        headless = run_flow(args.module, flow_name=args.flow, document=document, log=args.log)
    except ValueError as exc:
        # A document/config violation raises before anything runs; an
        # executed failure carries the run account (``.run``).
        if getattr(exc, "run", None) is None:
            return _fail(str(exc))
        traceback.print_exc()
        _report_run(exc.run, getattr(exc, "flow_name", args.flow or "?"))
        return EXIT_RUN_ERROR
    except (ImportError, OSError) as exc:
        return _fail(str(exc))
    except Exception as exc:
        traceback.print_exc()
        _report_run(getattr(exc, "run", None), getattr(exc, "flow_name", args.flow or "?"))
        return EXIT_RUN_ERROR

    _report_run(headless.run, headless.flow_name)
    try:
        shown = json.dumps(jsonable(headless.run.result), default=str)
    except Exception:  # pragma: no cover - jsonable's own fallbacks cover exotic types
        shown = repr(headless.run.result)
    print(f"result: {shown}")
    return EXIT_OK


def _first_doc_line(fn) -> str:
    doc = (inspect.getdoc(fn) or "").strip()
    return doc.splitlines()[0] if doc else ""


def _report_run(run, flow_name: str) -> None:
    """Print the run's account line: status, duration, log path."""
    if run is None:
        print(f"flow {flow_name}: error")
        return
    line = f"flow {flow_name}: {run.status}"
    if run.duration_ms is not None:
        line += f" ({run.duration_ms} ms)"
    print(line)
    if run.log:
        print(f"log: {run.log}")
