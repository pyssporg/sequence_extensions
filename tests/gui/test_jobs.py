"""Tests for JobManager using an injected fake worker."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from seq_ext_gui.contracts import JobRequest
from seq_ext_gui.jobs import TERMINAL_STATES, JobManager


def make_manager(tmp_path: Path, fake_worker: Path, **kwargs: float) -> JobManager:
    root = tmp_path / "project"
    root.mkdir(exist_ok=True)
    return JobManager(
        root,
        worker_cmd=[sys.executable, str(fake_worker)],
        **kwargs,
    )


async def wait_for(predicate, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        await asyncio.sleep(0.02)
    raise AssertionError("condition was not met before the timeout")


def terminal_status(manager: JobManager, job_id: str):
    status = manager.status(job_id)
    if status is None or status.state not in TERMINAL_STATES:
        return None
    return status


def test_execute_job_succeeds(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        job_id = await manager.start(JobRequest(flow_file="flow.py"))
        assert manager.status(job_id) is not None

        status = await wait_for(lambda: terminal_status(manager, job_id))
        assert status.state == "succeeded"
        assert status.result is not None and status.result.ok
        assert status.exit_code == 0

        directory = Path(status.log_dir).parent
        assert (directory / "request.json").is_file()
        assert (directory / "result.json").is_file()
        assert (directory / "stderr.log").is_file()
        assert list(Path(status.log_dir).glob("*.jsonl"))

        events = [event async for event in manager.stream(job_id)]
        assert events[0][0] == "status"
        assert events[0][1]["state"] == "succeeded"
        assert events[-1][0] == "done"
        assert events[-1][1]["result"]["ok"] is True
        logs = [data for event, data, _ in events if event == "log"]
        assert [record["record"]["event"] for record in logs] == ["start", "done"]

    asyncio.run(run())


def test_stream_replays_remaining_records(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        job_id = await manager.start(JobRequest(flow_file="flow.py"))
        await wait_for(lambda: terminal_status(manager, job_id))

        full = [event async for event in manager.stream(job_id)]
        replay = [event async for event in manager.stream(job_id, start_index=1)]
        full_logs = [event for event in full if event[0] == "log"]
        replay_logs = [event for event in replay if event[0] == "log"]
        assert [event[2] for event in full_logs] == [1, 2]
        assert [event[2] for event in replay_logs] == [2]
        assert replay[0][0] == "status"
        assert replay[-1][0] == "done"

    asyncio.run(run())


def test_failed_result_marks_job_failed(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        job_id = await manager.start(JobRequest(flow_file="fail.py"))
        status = await wait_for(lambda: terminal_status(manager, job_id))
        assert status.state == "failed"
        assert status.error == "boom"
        assert status.result is not None and status.result.ok is False

    asyncio.run(run())


def test_cancel_kills_and_is_idempotent(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker, job_timeout=60.0)
        job_id = await manager.start(JobRequest(flow_file="slow.py"))
        await wait_for(lambda: manager.status(job_id).state == "running")

        first = await manager.cancel(job_id)
        assert first is not None and first.state == "cancelled"
        second = await manager.cancel(job_id)
        assert second is not None and second.state == "cancelled"

        task = manager._jobs[job_id].task
        assert task is not None
        await asyncio.wait_for(task, timeout=5.0)
        status = manager.status(job_id)
        assert status.state == "cancelled"
        assert manager.status("does-not-exist") is None
        assert await manager.cancel("does-not-exist") is None

    asyncio.run(run())


def test_shutdown_cancels_unfinished_jobs(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker, job_timeout=60.0)
        job_id = await manager.start(JobRequest(flow_file="slow.py"))
        await wait_for(lambda: manager.status(job_id).state == "running")

        await manager.shutdown()

        status = manager.status(job_id)
        assert status is not None and status.state == "cancelled"
        task = manager._jobs[job_id].task
        assert task is not None
        await asyncio.wait_for(task, timeout=5.0)

    asyncio.run(run())


def test_cancel_finished_job_is_a_noop(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        job_id = await manager.start(JobRequest(flow_file="flow.py"))
        status = await wait_for(lambda: terminal_status(manager, job_id))
        assert status.state == "succeeded"
        again = await manager.cancel(job_id)
        assert again is not None and again.state == "succeeded"

    asyncio.run(run())


def test_job_timeout_marks_failed(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker, job_timeout=0.3)
        job_id = await manager.start(JobRequest(flow_file="slow.py"))
        status = await wait_for(
            lambda: terminal_status(manager, job_id),
            timeout=10.0,
        )
        assert status.state == "failed"
        assert status.error is not None and "timed out" in status.error

    asyncio.run(run())


def test_evaluate_uses_plan_mode(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        result = await manager.evaluate(JobRequest(flow_file="flow.py"))
        assert result.ok is True
        assert result.mode == "plan"

    asyncio.run(run())


def test_discover_uses_discover_mode(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        result = await manager.discover(JobRequest(flow_file="flow.py"))
        assert result.ok is True
        assert result.mode == "discover"

        jobs_dir = tmp_path / "project" / ".seq_ext_gui" / "jobs"
        request_path = next(jobs_dir.glob("*/request.json"))
        request = json.loads(request_path.read_text(encoding="utf-8"))
        assert request["mode"] == "discover"

    asyncio.run(run())


def test_execute_worker_crash_marks_failed(tmp_path: Path) -> None:
    async def run() -> None:
        root = tmp_path / "project"
        root.mkdir()
        manager = JobManager(
            root,
            worker_cmd=[sys.executable, "-c", "import sys; sys.exit(3)"],
        )
        job_id = await manager.start(JobRequest(flow_file="flow.py"))
        status = await wait_for(lambda: terminal_status(manager, job_id))
        assert status.state == "failed"
        assert status.error is not None and "exited with code 3" in status.error

    asyncio.run(run())


def test_evaluate_reports_worker_crash(tmp_path: Path) -> None:
    async def run() -> None:
        root = tmp_path / "project"
        root.mkdir()
        manager = JobManager(
            root,
            worker_cmd=[sys.executable, "-c", "import sys; sys.exit(3)"],
        )
        result = await manager.evaluate(JobRequest(flow_file="flow.py"))
        assert result.ok is False
        assert result.error_type == "WorkerExit"
        assert result.error is not None and "exited with code 3" in result.error

    asyncio.run(run())


def test_evaluate_timeout(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        result = await manager.evaluate(JobRequest(flow_file="slow.py"), timeout=0.3)
        assert result.ok is False
        assert result.error_type == "TimeoutError"
        assert result.error is not None and "timed out" in result.error

    asyncio.run(run())


def test_request_file_is_worker_contract(tmp_path: Path, fake_worker: Path) -> None:
    async def run() -> None:
        manager = make_manager(tmp_path, fake_worker)
        plan = {
            "schema": "flow-plan/2",
            "parameters": [{"name": "n", "type": "int", "value": 3}],
            "nodes": [],
            "edges": [],
            "options": {"max_workers": 2},
        }
        job_id = await manager.start(JobRequest(flow_file="flow.py", flow_name="root", plan=plan))
        status = await wait_for(lambda: terminal_status(manager, job_id))
        request = json.loads((Path(status.log_dir).parent / "request.json").read_text())
        assert request["mode"] == "execute"
        assert request["log_dir"] == status.log_dir
        assert request["flow_name"] == "root"
        assert request["plan"] == plan
        assert {"config_file", "config_text", "cwd", "overrides"}.isdisjoint(request)

    asyncio.run(run())
