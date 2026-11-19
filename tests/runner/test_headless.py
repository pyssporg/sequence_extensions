"""Headless run API: module loading, selection, the gate, and the run unit."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

from sequence_extensions.flow_runner import headless as headless_api
from sequence_extensions.flow_runner.headless import (
    HeadlessRun,
    load_flow_module,
    require_plan_document,
    run_flow,
    select_flow,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_FLOWS = REPO_ROOT / "tests" / "runner" / "flows.py"

ONE_NODE = """\
from sequence_extensions.flow import node

@node
def solo():
    \"\"\"Return seven.\"\"\"
    return 7
"""


def write_module(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------- #
# Module loading
# ---------------------------------------------------------------- #
def test_loads_a_dotted_module():
    module = load_flow_module("runner.flows")

    assert module.__name__ == "runner.flows"
    assert module.echo.__node__ == "echo"


def test_loads_a_py_file_by_path():
    module = load_flow_module(RUNNER_FLOWS)

    assert module.__name__.startswith("_flow_runner_")
    assert module.echo.__node__ == "echo"


def test_loads_a_package_directory(tmp_path):
    package = tmp_path / "flowpkg"
    package.mkdir()
    (package / "__init__.py").write_text(ONE_NODE, encoding="utf-8")

    try:
        module = load_flow_module(package)
    finally:
        sys.modules.pop("flowpkg", None)

    assert module.__name__ == "flowpkg"
    assert select_flow(module)[0] == "solo"


def test_rejects_a_non_py_file(tmp_path):
    notes = write_module(tmp_path, "notes.txt", "not python\n")

    with pytest.raises(ValueError, match="flow file must be a .py file"):
        load_flow_module(notes)


def test_missing_file_names_the_path(tmp_path):
    missing = tmp_path / "missing.py"

    with pytest.raises(FileNotFoundError, match="flow module not found"):
        load_flow_module(missing)


# ---------------------------------------------------------------- #
# Selection
# ---------------------------------------------------------------- #
def test_selects_the_only_node(tmp_path):
    module = load_flow_module(write_module(tmp_path, "solo.py", ONE_NODE))

    name, fn = select_flow(module)

    assert name == "solo"
    assert fn.__node__ == "solo"


def test_selects_one_node_by_name():
    module = load_flow_module("runner.flows")

    name, fn = select_flow(module, "bump")

    assert name == "bump"
    assert fn.__node__ == "bump"


def test_ambiguous_selection_lists_available_flows():
    module = load_flow_module("runner.flows")

    with pytest.raises(
        ValueError, match="no flow selected; 4 available: bump, double, echo, failing"
    ):
        select_flow(module)


def test_unknown_flow_names_the_module_and_alternatives():
    module = load_flow_module("runner.flows")

    with pytest.raises(
        ValueError,
        match="no flow 'nope' in module 'runner.flows'; available: bump, double, echo, failing",
    ):
        select_flow(module, "nope")


# ---------------------------------------------------------------- #
# The plan-schema gate
# ---------------------------------------------------------------- #
def test_require_plan_document_returns_the_same_object(default_options):
    document = {
        "schema": "flow-plan/2",
        "parameters": [],
        "nodes": [],
        "edges": [],
        "options": dict(default_options),
    }

    assert require_plan_document(document) is document


def test_require_plan_document_rejects_another_schema():
    with pytest.raises(ValueError, match="expected schema 'flow-plan/2', got 'flow-plan/1'"):
        require_plan_document({"schema": "flow-plan/1"})


# ---------------------------------------------------------------- #
# run_flow: plan only
# ---------------------------------------------------------------- #
def test_plan_only_returns_a_document_without_a_run(tmp_path):
    module = write_module(tmp_path, "solo.py", ONE_NODE)

    headless = run_flow(module, flow_name="solo", plan_only=True, log=tmp_path / "logs")

    assert isinstance(headless, HeadlessRun)
    assert dataclasses.is_dataclass(headless)
    with pytest.raises(dataclasses.FrozenInstanceError):
        headless.flow_name = "other"
    assert headless.flow_name == "solo"
    assert headless.document["schema"] == "flow-plan/2"
    assert headless.run is None
    assert not (tmp_path / "logs").exists()
    assert headless.to_dict() == {
        "flow_name": "solo",
        "plan": headless.document,
        "run": None,
    }


# ---------------------------------------------------------------- #
# run_flow: overrides
# ---------------------------------------------------------------- #
def test_overrides_are_applied_in_order():
    fresh = run_flow(
        "runner.flows",
        flow_name="echo",
        seed={"value": 1, "factor": 1},
        plan_only=True,
    ).document

    edited = run_flow(
        "runner.flows",
        flow_name="echo",
        document=fresh,
        overrides=[
            {
                "parameters": [{"name": "value", "value": 4}],
                "options": {"max_workers": 2},
            },
            {
                "parameters": [{"name": "value", "value": 5}],
                "options": {"max_workers": 4},
            },
        ],
        plan_only=True,
    ).document

    root = {entry["name"]: entry["value"] for entry in edited["parameters"]}

    assert root["value"] == 5
    assert edited["options"]["max_workers"] == 4
    # The supplied document was not mutated.
    original = {entry["name"]: entry["value"] for entry in fresh["parameters"]}
    assert original["value"] == 1


# ---------------------------------------------------------------- #
# run_flow: cwd
# ---------------------------------------------------------------- #
def test_cwd_is_entered_and_restored(tmp_path):
    write_module(
        tmp_path,
        "probe.py",
        "from pathlib import Path\n"
        "from sequence_extensions.flow import node\n"
        "@node\n"
        "def where():\n"
        "    return str(Path.cwd())\n",
    )
    previous = Path.cwd()

    headless = run_flow("probe.py", flow_name="where", cwd=tmp_path, log=tmp_path / "logs")

    assert Path(headless.run.result) == tmp_path.resolve()
    assert Path.cwd() == previous


def test_cwd_is_restored_when_selection_fails(tmp_path):
    module = write_module(tmp_path, "solo.py", ONE_NODE)
    previous = Path.cwd()

    with pytest.raises(ValueError, match="no flow 'missing'"):
        run_flow(module, flow_name="missing", cwd=tmp_path)

    assert Path.cwd() == previous


def test_accepts_a_loaded_module_without_reimporting(tmp_path, monkeypatch):
    path = write_module(tmp_path, "solo.py", ONE_NODE)
    module = load_flow_module(path)

    def refuse(_source):
        raise AssertionError("run_flow re-imported an already-loaded module")

    monkeypatch.setattr(headless_api, "load_flow_module", refuse)

    headless = run_flow(module, flow_name="solo", log=tmp_path / "logs")

    assert headless.run.result == 7


# ---------------------------------------------------------------- #
# run_flow: projection
# ---------------------------------------------------------------- #
def test_to_dict_projects_flow_plan_and_run(tmp_path):
    logs = tmp_path / "logs"

    headless = run_flow(
        "runner.flows",
        flow_name="echo",
        seed={"value": 2, "factor": 3},
        log=logs,
    )

    projected = headless.to_dict()
    assert set(projected) == {"flow_name", "plan", "run"}
    assert projected["flow_name"] == "echo"
    assert projected["plan"]["schema"] == "flow-plan/2"

    run = projected["run"]
    assert set(run) == {
        "status",
        "result",
        "run_id",
        "node",
        "duration_ms",
        "attempt",
        "started",
        "ended",
        "log",
        "error",
        "failed_nodes",
    }
    assert run["status"] == "ok"
    assert run["result"] == 6
    assert run["node"] == "echo"
    assert run["error"] is None
    assert run["failed_nodes"] == []
    assert Path(run["log"]).exists()


def test_result_is_projected_through_jsonable(tmp_path):
    module = write_module(
        tmp_path,
        "shapes.py",
        "from sequence_extensions.flow import node\n"
        "@node\n"
        "def shapes():\n"
        "    return {'items': {3, 1, 2}}\n",
    )

    headless = run_flow(module, flow_name="shapes", log=tmp_path / "logs")

    assert headless.to_dict()["run"]["result"] == {"items": [1, 2, 3]}
