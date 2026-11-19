"""Shared fixtures: a tiny project whose flow is fast and deterministic."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

SAMPLE_FLOW = '''\
"""Sample flow used by the test suite."""

from __future__ import annotations

from sequence_extensions.flow import gather, node


@node
def double(x: int) -> int:
    """Double one value.

    This second line must not leak into the card summary.
    """
    return x * 2


@node
def scale(value: int, factor: int = 1) -> int:
    return value * factor


@node
def root(n: int = 2, factor: int = 3) -> list:
    doubled = [double.submit(i) for i in range(n)]
    # factor is left unset so the GUI can override it.
    return gather([scale.submit(item) for item in doubled])
'''

REQUIRED_FLOW = '''\
"""Sample flow with a required root input."""

from __future__ import annotations

from pathlib import Path

from sequence_extensions.flow import node


@node
def needs_input(cases_dir: Path) -> str:
    return str(cases_dir)
'''

FAILING_FLOW = '''\
"""Sample flow whose child always fails."""

from __future__ import annotations

from sequence_extensions.flow import node


@node
def boom() -> None:
    raise ValueError("kaboom")


@node
def failing() -> None:
    return boom.submit()
'''

TYPED_FLOW = '''\
"""Sample flow with one root parameter of each scalar type."""

from __future__ import annotations

from sequence_extensions.flow import node


@node
def typed(n: int = 1, ratio: float = 1.5, flag: bool = False, label: str = "x") -> str:
    return f"{n}:{ratio}:{flag}:{label}"
'''

#: A hand-written ``flow-plan/2`` seed: the node values a user edited, keyed
#: by identity.  The GUI imports a document like this, and ``engine.plan``
#: folds it onto fresh code.
SAMPLE_PLAN: dict[str, Any] = {
    "schema": "flow-plan/2",
    "parameters": [{"name": "n", "type": "int", "required": False, "default": 2, "value": 3}],
    "nodes": [
        {
            "name": "scale",
            "path": ["root", "scale"],
            "instance": instance,
            "params": [
                {"name": "factor", "type": "int", "required": False, "default": 1, "value": 10}
            ],
            "policy": {"retries": 2},
        }
        for instance in (1, 2, 3)
    ],
    "edges": [],
    "options": {"max_workers": 2},
}


@dataclass(frozen=True)
class SampleProject:
    root: Path
    flow: Path
    required: Path
    failing: Path
    typed: Path

    def write_plan(self, document: dict[str, Any], name: str = "plan.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return path


FAKE_WORKER = """
import json
import sys
import time
from pathlib import Path

request_path = Path(sys.argv[1])
result_path = Path(sys.argv[2])
request = json.loads(request_path.read_text(encoding="utf-8"))
log_dir = request.get("log_dir")
log_path = None
if log_dir:
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "run.jsonl"
    log_path.write_text(
        json.dumps({"node": "root", "event": "start"}) + "\\n", encoding="utf-8"
    )

name = Path(request["flow_file"]).name
if name == "slow.py":
    time.sleep(30)
if name == "fail.py":
    result_path.write_text(
        json.dumps({"ok": False, "mode": request.get("mode"), "error": "boom"}),
        encoding="utf-8",
    )
    raise SystemExit(0)
time.sleep(0.2)
if log_path is not None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"node": "root", "event": "done"}) + "\\n")
if request.get("mode") == "discover":
    result_path.write_text(
        json.dumps(
            {
                "ok": True,
                "mode": "discover",
                "nodes": [
                    {"name": "root", "summary": "Root node.", "signature": "() -> None"}
                ],
            }
        ),
        encoding="utf-8",
    )
    raise SystemExit(0)
result = {
    "ok": True,
    "mode": request.get("mode", "plan"),
    "flow_name": request.get("flow_name") or "root",
    "plan": request.get("plan"),
    "duration_ms": 1,
}
result_path.write_text(json.dumps(result), encoding="utf-8")
"""


@pytest.fixture
def fake_worker(tmp_path: Path) -> Path:
    path = tmp_path / "fake_worker.py"
    path.write_text(FAKE_WORKER, encoding="utf-8")
    return path


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def sample_project(tmp_path: Path) -> SampleProject:
    root = tmp_path / "project"
    root.mkdir()
    flow = root / "flow.py"
    flow.write_text(SAMPLE_FLOW, encoding="utf-8")
    required = root / "required.py"
    required.write_text(REQUIRED_FLOW, encoding="utf-8")
    failing = root / "failing.py"
    failing.write_text(FAILING_FLOW, encoding="utf-8")
    typed = root / "typed.py"
    typed.write_text(TYPED_FLOW, encoding="utf-8")
    return SampleProject(root=root, flow=flow, required=required, failing=failing, typed=typed)


@pytest.fixture
def sample_plan(sample_project: SampleProject) -> dict[str, Any]:
    """A full ``flow-plan/2`` document generated from the hand-written seed."""
    from seq_ext_gui.contracts import WorkerRequest, to_document
    from seq_ext_gui.engine import plan

    result = plan(
        WorkerRequest(
            mode="plan",
            flow_file=str(sample_project.flow),
            flow_name="root",
            plan=SAMPLE_PLAN,
        )
    )
    assert result.ok, result.error
    assert result.plan is not None
    return to_document(result.plan)
