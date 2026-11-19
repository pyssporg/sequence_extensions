"""HTTP API tests using a fake worker; integration tests for the real worker."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from seq_ext_gui.app import create_app

MINIMAL_PLAN: dict[str, Any] = {
    "schema": "flow-plan/2",
    "parameters": [],
    "nodes": [],
    "edges": [],
    "options": {},
}

TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


@pytest.fixture
def client(sample_project, fake_worker: Path) -> Iterator[TestClient]:
    app = create_app(
        sample_project.root,
        worker_cmd=[sys.executable, str(fake_worker)],
        evaluate_timeout=10.0,
        job_timeout=10.0,
    )
    with TestClient(app) as test_client:
        yield test_client


def parse_sse(lines: Iterable[str]) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []
    event: str | None = None
    data: Any = None
    for line in lines:
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data = json.loads(line.split(":", 1)[1].strip())
        elif line == "":
            if event is not None:
                events.append((event, data))
            event = None
            data = None
    return events


def wait_for_status(client: TestClient, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        if body["state"] in TERMINAL_STATES:
            return body
        time.sleep(0.02)
    raise AssertionError(f"job {job_id} did not finish")


def test_health(client: TestClient, sample_project) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["version"]
    assert body["project_root"] == str(sample_project.root)


def test_static_assets_are_not_cached(client: TestClient) -> None:
    for name in ("app.js", "graph.js", "styles.css"):
        response = client.get(f"/static/{name}")
        assert response.status_code == 200
        assert "no-store" in response.headers["cache-control"]


def test_tree(client: TestClient) -> None:
    response = client.get("/api/tree")
    assert response.status_code == 200
    body = response.json()
    assert body["path"] == ""
    names = [entry["name"] for entry in body["entries"]]
    assert names == ["failing.py", "flow.py", "required.py", "typed.py"]
    assert all(entry["kind"] == "file" for entry in body["entries"])


def test_file_reads_plans_and_flow_modules(client: TestClient, sample_project) -> None:
    plan_path = sample_project.write_plan(MINIMAL_PLAN)
    response = client.get("/api/file", params={"path": plan_path.name})
    assert response.status_code == 200
    assert json.loads(response.json()["content"])["schema"] == "flow-plan/2"

    response = client.get("/api/file", params={"path": "flow.py"})
    assert response.status_code == 200
    assert "@node" in response.json()["content"]


def test_toml_files_are_not_readable(client: TestClient, sample_project) -> None:
    (sample_project.root / "legacy.toml").write_text("[run]\n", encoding="utf-8")

    response = client.get("/api/file", params={"path": "legacy.toml"})
    assert response.status_code == 400
    assert ".py/.json" in response.json()["detail"]


def test_put_file_route_is_removed(client: TestClient) -> None:
    response = client.put(
        "/api/file",
        params={"path": "plan.json"},
        json={"content": '{"schema": "flow-plan/2"}'},
    )
    assert response.status_code == 405


def test_file_paths_outside_root_are_400(client: TestClient) -> None:
    assert client.get("/api/file", params={"path": "../outside.txt"}).status_code == 400
    assert client.get("/api/tree", params={"path": ".."}).status_code == 400
    response = client.post("/api/evaluate", json={"flow_file": "../outside.py"})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "extra",
    [
        {"config_file": "sample.toml"},
        {"config_text": "[run]\n"},
        {"cwd": "."},
        {"overrides": {}},
    ],
)
def test_removed_job_fields_are_rejected(client: TestClient, extra: dict) -> None:
    payload = {"flow_file": "flow.py", **extra}
    assert client.post("/api/evaluate", json=payload).status_code == 422
    assert client.post("/api/execute", json=payload).status_code == 422


def test_evaluate_returns_the_worker_result(client: TestClient) -> None:
    response = client.post(
        "/api/evaluate",
        json={"flow_file": "flow.py", "flow_name": "root", "plan": MINIMAL_PLAN},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mode"] == "plan"
    assert body["flow_name"] == "root"
    assert body["plan"]["schema"] == "flow-plan/2"
    # PlanOptions fills concrete defaults for a document that omitted them.
    assert body["plan"]["options"]["max_workers"] == 16
    assert body["plan"]["options"]["timeout"] is None


def test_discover_returns_node_cards(client: TestClient) -> None:
    response = client.post("/api/discover", json={"flow_file": "flow.py"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["mode"] == "discover"
    assert body["nodes"] == [
        {"name": "root", "summary": "Root node.", "signature": "() -> None", "params": []}
    ]


def test_discover_paths_outside_root_are_400(client: TestClient) -> None:
    response = client.post("/api/discover", json={"flow_file": "../outside.py"})
    assert response.status_code == 400


@pytest.mark.integration
def test_discover_rejects_a_non_python_file(sample_project) -> None:
    (sample_project.root / "notes.txt").write_text("not a flow\n", encoding="utf-8")

    with TestClient(create_app(sample_project.root)) as test_client:
        response = test_client.post("/api/discover", json={"flow_file": "notes.txt"})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["mode"] == "discover"
    assert ".py" in body["error"]


def test_execute_job_status_and_sse(client: TestClient) -> None:
    response = client.post(
        "/api/execute",
        json={"flow_file": "flow.py", "flow_name": "root", "plan": MINIMAL_PLAN},
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert isinstance(job_id, str) and job_id

    status = wait_for_status(client, job_id)
    assert status["state"] == "succeeded"
    assert status["result"]["ok"] is True

    with client.stream("GET", f"/api/jobs/{job_id}/events") as stream:
        assert stream.status_code == 200
        assert stream.headers["content-type"].startswith("text/event-stream")
        events = parse_sse(stream.iter_lines())

    assert events[0] == ("status", {"state": "succeeded"})
    assert events[-1][0] == "done"
    assert events[-1][1]["result"]["ok"] is True
    logs = [data for event, data in events if event == "log"]
    assert [record["record"]["event"] for record in logs] == ["start", "done"]

    with client.stream(
        "GET",
        f"/api/jobs/{job_id}/events",
        headers={"Last-Event-ID": "1"},
    ) as stream:
        replay = parse_sse(stream.iter_lines())
    replay_logs = [data for event, data in replay if event == "log"]
    assert [record["record"]["event"] for record in replay_logs] == ["done"]


def test_cancel_endpoint(client: TestClient) -> None:
    response = client.post("/api/execute", json={"flow_file": "slow.py"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        state = client.get(f"/api/jobs/{job_id}").json()["state"]
        if state == "running":
            break
        time.sleep(0.02)

    response = client.post(f"/api/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["state"] == "cancelled"
    response = client.post(f"/api/jobs/{job_id}/cancel")
    assert response.status_code == 200
    assert response.json()["state"] == "cancelled"

    assert client.get("/api/jobs/missing").status_code == 404
    assert client.post("/api/jobs/missing/cancel").status_code == 404


def test_index_without_static_dir(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code in {200, 404}


@pytest.mark.integration
def test_evaluate_sample_project_with_real_worker(sample_project) -> None:
    if (
        importlib.util.find_spec("seq_ext_gui.worker") is None
        or importlib.util.find_spec("seq_ext_gui.engine") is None
    ):
        pytest.skip("real worker/engine modules are not installed yet")

    with TestClient(create_app(sample_project.root)) as test_client:
        response = test_client.post(
            "/api/evaluate",
            json={"flow_file": "flow.py", "flow_name": "root"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True, body
    assert body["plan"] is not None
    assert body["plan"]["schema"] == "flow-plan/2"
    assert "root" not in body["plan"]
    assert body["plan"]["options"]["max_workers"] == 16
    assert {param["name"] for param in body["plan"]["parameters"]} == {"n", "factor"}


@pytest.mark.integration
def test_execute_round_trips_an_imported_plan(sample_project) -> None:
    seed = {
        "schema": "flow-plan/2",
        "parameters": [{"name": "n", "type": "int", "required": False, "default": 2, "value": 2}],
        "nodes": [],
        "edges": [],
        "options": {"max_workers": 1},
    }

    with TestClient(create_app(sample_project.root)) as test_client:
        response = test_client.post(
            "/api/evaluate",
            json={"flow_file": "flow.py", "flow_name": "root", "plan": seed},
        )
        assert response.status_code == 200
        planned = response.json()
        assert planned["ok"] is True, planned
        assert planned["plan"]["options"]["max_workers"] == 1

        response = test_client.post(
            "/api/execute",
            json={
                "flow_file": "flow.py",
                "flow_name": "root",
                "plan": planned["plan"],
            },
        )
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        status = wait_for_status(test_client, job_id)

    assert status["state"] == "succeeded", status
    assert status["result"]["run"]["result"] == [0, 2]


def test_project_root_can_be_switched(sample_project, fake_worker: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    other.mkdir()
    (other / "other.py").write_text("print('other')\n", encoding="utf-8")
    app = create_app(sample_project.root, worker_cmd=[sys.executable, str(fake_worker)])

    with TestClient(app) as test_client:
        assert test_client.get("/api/health").json()["project_root"] == str(sample_project.root)

        response = test_client.put("/api/root", json={"path": str(other)})
        assert response.status_code == 200, response.text
        assert response.json()["project_root"] == str(other)
        assert test_client.get("/api/health").json()["project_root"] == str(other)

        tree = test_client.get("/api/tree?path=").json()
        assert [entry["name"] for entry in tree["entries"]] == ["other.py"]
        assert test_client.get("/api/file?path=flow.py").status_code == 400

        assert test_client.put("/api/root", json={"path": "relative"}).status_code == 400
        missing = tmp_path / "missing"
        assert test_client.put("/api/root", json={"path": str(missing)}).status_code == 400
        assert test_client.get("/api/health").json()["project_root"] == str(other)

        started = test_client.post(
            "/api/execute", json={"flow_file": "other.py", "plan": MINIMAL_PLAN}
        )
        assert started.status_code == 200, started.text
        job = started.json()["job_id"]
        assert (other / ".seq_ext_gui" / "jobs" / job).is_dir()
        test_client.post(f"/api/jobs/{job}/cancel")

        back = test_client.put("/api/root", json={"path": str(sample_project.root)})
        assert back.status_code == 200
        assert test_client.get("/api/file?path=flow.py").status_code == 200
