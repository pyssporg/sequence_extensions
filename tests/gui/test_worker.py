"""Worker subprocess protocol test."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from seq_ext_gui.contracts import WorkerRequest, WorkerResult, to_document
from seq_ext_gui.worker import _dispatch


def _run_worker(request: WorkerRequest, tmp_path: Path) -> WorkerResult:
    request_path = tmp_path / "request.json"
    result_path = tmp_path / "result.json"
    request_path.write_text(request.model_dump_json(by_alias=True), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    completed = subprocess.run(
        [sys.executable, "-m", "seq_ext_gui.worker", str(request_path), str(result_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    return WorkerResult.model_validate_json(result_path.read_text(encoding="utf-8"))


def test_worker_cli_writes_a_parseable_result(tmp_path: Path, sample_project) -> None:
    plan = {
        "schema": "flow-plan/2",
        "parameters": [{"name": "n", "type": "int", "required": False, "default": 2, "value": 3}],
        "nodes": [
            {
                "name": "scale",
                "path": ["root", "scale"],
                "instance": 1,
                "params": [{"name": "factor", "type": "int", "default": 1, "value": 10}],
                "policy": {"retries": 2},
            }
        ],
        "edges": [],
        "options": {"max_workers": 2},
    }
    request = WorkerRequest(
        mode="plan",
        flow_file=str(sample_project.flow),
        flow_name="root",
        plan=plan,
    )
    result = _run_worker(request, tmp_path)
    assert result.ok, result.error
    assert result.mode == "plan"
    assert result.plan is not None
    assert result.plan["schema"] == "flow-plan/2"
    document = to_document(result.plan)
    parameters = {param["name"]: param["value"] for param in document["parameters"]}
    assert parameters["n"] == 3
    assert document["options"]["max_workers"] == 2
    scale = next(node for node in result.plan["nodes"] if node["name"] == "scale")
    assert scale["policy"]["retries"] == 2


def test_worker_cli_dispatches_discovery(tmp_path: Path, sample_project) -> None:
    request = WorkerRequest(mode="discover", flow_file=str(sample_project.flow))

    result = _run_worker(request, tmp_path)

    assert result.ok, result.error
    assert result.mode == "discover"
    cards = {card.name: card for card in result.nodes}
    assert set(cards) == {"double", "root", "scale"}
    assert cards["scale"].signature == "(value: int, factor: int = 1) -> int"


def test_worker_dispatch_rejects_an_unknown_mode(sample_project) -> None:
    request = WorkerRequest.model_construct(
        mode="bogus",
        flow_file=str(sample_project.flow),
    )

    with pytest.raises(ValueError, match="unknown worker mode"):
        _dispatch(request)
