"""Engine tests: plan documents (``flow-plan/2``) and plan-based execution."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from seq_ext_gui.contracts import WorkerRequest, to_document
from seq_ext_gui.engine import _override_from_seed, discover, execute, plan

DEFAULT_OPTIONS = {
    "max_workers": 16,
    "summary": False,
    "fixed_clock": False,
    "retries": 0,
    "retry_delay_seconds": 0.0,
    "timeout": None,
}


def _request(sample_project, **kwargs) -> WorkerRequest:
    values = {"mode": "plan", "flow_file": str(sample_project.flow), "flow_name": "root"}
    values.update(kwargs)
    return WorkerRequest(**values)


def test_plan_requires_a_flow_when_ambiguous(sample_project) -> None:
    result = plan(WorkerRequest(mode="plan", flow_file=str(sample_project.flow)))

    assert result.ok is False
    assert {"double", "root", "scale"} <= set(result.available_flows)
    assert "no flow selected" in (result.error or "")


def test_plan_emits_the_v2_document_shape(sample_project) -> None:
    result = plan(_request(sample_project))

    assert result.ok, result.error
    assert result.plan is not None
    document = to_document(result.plan)
    assert document["schema"] == "flow-plan/2"
    assert "root" not in document
    assert document["options"] == DEFAULT_OPTIONS
    assert {node["name"] for node in document["nodes"]} >= {"double", "scale", "gather"}
    assert all(node["path"][0] == "root" for node in document["nodes"] if node["name"] != "gather")
    assert {node["instance"] for node in document["nodes"] if node["name"] == "scale"} == {1, 2}
    assert document["edges"]


def test_plan_applies_the_editability_heuristic(sample_project) -> None:
    result = plan(_request(sample_project))

    assert result.ok, result.error
    assert result.plan is not None
    scale = next(node for node in result.plan["nodes"] if node["name"] == "scale")
    factor = next(param for param in scale["params"] if param["name"] == "factor")
    assert factor["editable"] is True

    double = next(node for node in result.plan["nodes"] if node["name"] == "double")
    bound = next(param for param in double["params"] if param["name"] == "x")
    assert bound["editable"] is False
    assert bound["note"] == "set by flow code"

    # Instances are edited independently, so no name-fan-out warning remains.
    assert not any("every instance" in warning for warning in result.warnings)


def test_plan_imports_a_hand_written_document(sample_project) -> None:
    seed = {
        "schema": "flow-plan/2",
        "parameters": [{"name": "n", "type": "int", "required": False, "default": 2, "value": 3}],
        "nodes": [
            {
                "name": "scale",
                "path": ["root", "scale"],
                "instance": 1,
                "params": [{"name": "factor", "type": "int", "default": 1, "value": 10}],
                "policy": {"retries": 2, "timeout": 5.0},
            }
        ],
        "edges": [],
        "options": {"max_workers": 4, "summary": True},
    }

    result = plan(_request(sample_project, plan=seed))

    assert result.ok, result.error
    assert result.plan is not None
    document = to_document(result.plan)
    parameters = {param["name"]: param["value"] for param in document["parameters"]}
    assert parameters["n"] == 3
    assert document["options"]["max_workers"] == 4
    assert document["options"]["summary"] is True
    assert document["options"]["fixed_clock"] is False

    scale_instances = [node for node in result.plan["nodes"] if node["name"] == "scale"]
    assert len(scale_instances) == 3
    edited = next(node for node in scale_instances if node["instance"] == 1)
    assert edited["policy"]["retries"] == 2
    assert edited["policy"]["timeout"] == 5.0
    assert edited["policy"]["retry_delay_seconds"] == 0.0
    factor = next(param for param in edited["params"] if param["name"] == "factor")
    assert factor["value"] == 10
    # Editability comes from fresh code values, not the imported edit.
    assert factor["editable"] is True

    # The edit targets one occurrence; its siblings keep the fresh defaults.
    for node in scale_instances:
        if node["instance"] == 1:
            continue
        assert node["policy"]["retries"] == 0
        assert node["policy"]["timeout"] is None
        other = next(param for param in node["params"] if param["name"] == "factor")
        assert other["value"] == 1


def test_override_targets_the_selected_identity_only(sample_project) -> None:
    fresh = plan(_request(sample_project))
    assert fresh.ok, fresh.error
    assert fresh.plan is not None
    document = to_document(fresh.plan)
    seed = copy.deepcopy(document)
    selected = next(
        node for node in seed["nodes"] if node["name"] == "scale" and node["instance"] == 1
    )
    selected["params"][0]["value"] = 10
    selected["policy"]["retries"] = 2

    override, warnings = _override_from_seed(seed, document, {})

    assert not warnings
    assert override["nodes"] == [
        {
            "name": "scale",
            "path": ["root", "scale"],
            "instance": 1,
            "params": [{"name": "factor", "value": 10}],
            "policy": {"retries": 2},
        }
    ]


def test_override_skips_unchanged_values(sample_project) -> None:
    fresh = plan(_request(sample_project))
    assert fresh.ok, fresh.error
    assert fresh.plan is not None
    document = to_document(fresh.plan)

    override, warnings = _override_from_seed(document, document, {})

    assert not warnings
    assert "nodes" not in override


def test_stale_identity_is_warned_and_not_applied_name_wide(sample_project) -> None:
    seed = {
        "schema": "flow-plan/2",
        "nodes": [
            {
                "name": "scale",
                "path": ["root", "scale"],
                "instance": 99,
                "params": [{"name": "factor", "value": 10}],
                "policy": {"retries": 2},
            }
        ],
    }

    result = plan(_request(sample_project, plan=seed))

    assert result.ok, result.error
    assert any(
        "node scale #99 no longer exists in the re-planned flow" in warning
        for warning in result.warnings
    )
    assert result.plan is not None
    for node in result.plan["nodes"]:
        if node["name"] != "scale":
            continue
        assert node["policy"]["retries"] == 0
        factor = next(param for param in node["params"] if param["name"] == "factor")
        assert factor["value"] == 1


def test_legacy_node_seed_is_skipped_with_a_warning(sample_project) -> None:
    seed = {
        "schema": "flow-plan/2",
        "parameters": [{"name": "n", "type": "int", "required": False, "default": 2, "value": 3}],
        "nodes": [
            {
                "name": "scale",
                "params": [{"name": "factor", "value": 10}],
                "policy": {"retries": 2},
            }
        ],
    }

    result = plan(_request(sample_project, plan=seed))

    assert result.ok, result.error
    assert any("node scale has no identity" in warning for warning in result.warnings)
    assert result.plan is not None
    # Root parameters still apply.
    parameters = {param["name"]: param["value"] for param in result.plan["parameters"]}
    assert parameters["n"] == 3
    for node in result.plan["nodes"]:
        if node["name"] != "scale":
            continue
        assert node["policy"]["retries"] == 0
        factor = next(param for param in node["params"] if param["name"] == "factor")
        assert factor["value"] == 1


def test_plan_rejects_a_non_v2_seed(sample_project) -> None:
    result = plan(_request(sample_project, plan={"schema": "flow-plan/1"}))

    assert result.ok is False
    assert "flow-plan/2" in (result.error or "")


def test_plan_reports_missing_required_root_input(sample_project) -> None:
    result = plan(
        WorkerRequest(
            mode="plan",
            flow_file=str(sample_project.required),
            flow_name="needs_input",
        )
    )

    assert result.ok is False
    assert "missing required root parameter(s): cases_dir" in (result.error or "")


def test_plan_rejects_unknown_root_parameters(sample_project) -> None:
    seed = {
        "schema": "flow-plan/2",
        "parameters": [{"name": "bogus", "value": 1}],
    }

    result = plan(_request(sample_project, plan=seed))

    assert result.ok is False
    assert "unknown root parameter" in (result.error or "")


def test_plan_round_trips_a_path_parameter(sample_project) -> None:
    seed = {
        "schema": "flow-plan/2",
        "parameters": [
            {
                "name": "cases_dir",
                "type": "Path",
                "required": True,
                "value": {"path": "cases"},
            }
        ],
    }

    planned = plan(
        WorkerRequest(
            mode="plan",
            flow_file=str(sample_project.required),
            flow_name="needs_input",
            plan=seed,
        )
    )

    assert planned.ok, planned.error
    assert planned.plan is not None
    parameter = next(param for param in planned.plan["parameters"] if param["name"] == "cases_dir")
    assert parameter["value"]["path"] == "cases"
    assert parameter["value"]["sha256"] is None

    document = json.loads(json.dumps(to_document(planned.plan)))
    result = execute(
        WorkerRequest(
            mode="execute",
            flow_file=str(sample_project.required),
            flow_name="needs_input",
            plan=document,
        )
    )
    assert result.ok, result.error
    assert result.run is not None
    assert result.run.result == "cases"


def test_execute_requires_a_plan(sample_project) -> None:
    result = execute(_request(sample_project, mode="execute"))

    assert result.ok is False
    assert result.error == "execute requires a plan"


def test_discover_lists_every_node_card(sample_project) -> None:
    result = discover(WorkerRequest(mode="discover", flow_file=str(sample_project.flow)))

    assert result.ok, result.error
    assert result.mode == "discover"
    cards = {card.name: card for card in result.nodes}
    assert set(cards) == {"double", "root", "scale"}

    assert cards["double"].summary == "Double one value."
    assert cards["double"].signature == "(x: int) -> int"
    assert cards["scale"].summary == ""
    assert cards["scale"].signature == "(value: int, factor: int = 1) -> int"
    assert cards["root"].signature == "(n: int = 2, factor: int = 3) -> list"


def test_discover_reports_root_parameter_specs(sample_project) -> None:
    result = discover(WorkerRequest(mode="discover", flow_file=str(sample_project.flow)))

    assert result.ok, result.error
    cards = {card.name: card for card in result.nodes}
    root = [(p.name, p.type, p.required, p.default) for p in cards["root"].params]
    assert root == [("n", "int", False, 2), ("factor", "int", False, 3)]
    scale = [(p.name, p.type, p.required, p.default) for p in cards["scale"].params]
    assert scale == [("value", "int", True, None), ("factor", "int", False, 1)]
    assert all(p.default_note is None for p in cards["root"].params)


def test_discover_reports_a_required_path_parameter(sample_project) -> None:
    result = discover(
        WorkerRequest(
            mode="discover",
            flow_file=str(sample_project.required),
        )
    )

    assert result.ok, result.error
    (card,) = result.nodes
    assert card.name == "needs_input"
    assert card.signature == "(cases_dir: Path) -> str"
    (param,) = card.params
    assert param.name == "cases_dir"
    assert param.type == "Path"
    assert param.required is True
    assert param.default is None
    assert param.default_note is None


def test_discover_rejects_a_non_python_file(sample_project) -> None:
    notes = sample_project.root / "notes.txt"
    notes.write_text("not a flow\n", encoding="utf-8")

    result = discover(WorkerRequest(mode="discover", flow_file=str(notes)))

    assert result.ok is False
    assert result.mode == "discover"
    assert ".py" in (result.error or "")


def test_execute_round_trips_the_plan_document(sample_project, sample_plan) -> None:
    document = json.loads(json.dumps(sample_plan))
    log_dir = sample_project.root / "logs"

    result = execute(
        WorkerRequest(
            mode="execute",
            flow_file=str(sample_project.flow),
            flow_name="root",
            plan=document,
            log_dir=str(log_dir),
        )
    )

    assert result.ok, result.error
    assert result.run is not None
    assert result.run.status == "ok"
    # double(i) for i in range(3) is [0, 2, 4]; the imported plan sets factor=10.
    assert result.run.result == [0, 20, 40]
    assert result.run.log is not None
    assert Path(result.run.log).parent == log_dir
    assert list(log_dir.glob("*.jsonl"))
    assert result.plan is not None
    scale = next(node for node in result.plan["nodes"] if node["name"] == "scale")
    assert scale["policy"]["retries"] == 2


def test_execute_maps_flow_failure_to_result(sample_project, tmp_path: Path) -> None:
    planned = plan(
        WorkerRequest(
            mode="plan",
            flow_file=str(sample_project.failing),
            flow_name="failing",
        )
    )
    assert planned.ok, planned.error
    assert planned.plan is not None

    result = execute(
        WorkerRequest(
            mode="execute",
            flow_file=str(sample_project.failing),
            flow_name="failing",
            plan=to_document(planned.plan),
            log_dir=str(tmp_path / "logs"),
        )
    )

    assert result.ok is False
    assert result.run is not None
    assert result.run.status == "error"
    assert "kaboom" in (result.error or "")
    assert "kaboom" in (result.run.error or "")
    assert result.run.failed_nodes == [["failing", "boom"]]
    assert result.traceback
