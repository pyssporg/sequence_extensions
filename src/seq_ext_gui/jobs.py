"""Job lifecycle, worker subprocess supervision, and run-log tailing."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO

from pydantic import ValidationError

from .contracts import JobRequest, JobStatus, WorkerRequest, WorkerResult

TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


class _ResultError(Exception):
    """Raised when a worker result file is missing or malformed."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class _Job:
    id: str
    directory: Path
    request_path: Path
    result_path: Path
    stderr_path: Path
    log_dir: Path
    state: str = "queued"
    created: str = field(default_factory=_now)
    started: str | None = None
    ended: str | None = None
    exit_code: int | None = None
    error: str | None = None
    result: WorkerResult | None = None
    process: asyncio.subprocess.Process | None = None
    task: asyncio.Task[None] | None = None
    stderr_file: BinaryIO | None = None


class JobManager:
    """Run each evaluate/execute in a fresh worker process."""

    def __init__(
        self,
        project_root: Path,
        *,
        worker_cmd: list[str] | None = None,
        evaluate_timeout: float = 120.0,
        job_timeout: float = 600.0,
    ) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self.worker_cmd = (
            list(worker_cmd)
            if worker_cmd is not None
            else [sys.executable, "-m", "seq_ext_gui.worker"]
        )
        self.evaluate_timeout = float(evaluate_timeout)
        self.timeout = float(job_timeout)
        self._jobs: dict[str, _Job] = {}

    def set_root(self, root: Path) -> None:
        """Use *root* for job directories created from now on."""
        self.project_root = Path(root).expanduser().resolve()

    def status(self, job_id: str) -> JobStatus | None:
        job = self._jobs.get(job_id)
        return None if job is None else self._status(job)

    async def evaluate(
        self,
        request: JobRequest,
        *,
        timeout: float | None = None,
    ) -> WorkerResult:
        """Run one plan-mode worker to completion and return its result."""
        return await self._run(
            request, mode="plan", activity="evaluation", timeout=timeout, prefix="eval"
        )

    async def discover(
        self,
        request: JobRequest,
        *,
        timeout: float | None = None,
    ) -> WorkerResult:
        """Run one discover-mode worker to completion and return its result."""
        return await self._run(
            request, mode="discover", activity="discovery", timeout=timeout, prefix="discover"
        )

    async def _run(
        self,
        request: JobRequest,
        *,
        mode: str,
        activity: str,
        timeout: float | None,
        prefix: str,
    ) -> WorkerResult:
        job = self._create(f"{prefix}-{uuid.uuid4().hex}", request)
        worker_request = WorkerRequest(mode=mode, **request.model_dump(exclude_unset=True))
        self._write_request(job, worker_request)
        limit = self.evaluate_timeout if timeout is None else float(timeout)

        try:
            process = await asyncio.create_subprocess_exec(
                *self.worker_cmd,
                str(job.request_path),
                str(job.result_path),
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as exc:
            return WorkerResult(
                ok=False,
                mode=mode,
                error=f"cannot start worker: {exc}",
                error_type=type(exc).__name__,
            )

        try:
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=limit)
        except TimeoutError:
            await self._terminate(process)
            return WorkerResult(
                ok=False,
                mode=mode,
                error=f"{activity} timed out after {limit:g} s",
                error_type="TimeoutError",
            )

        text = stderr.decode("utf-8", "replace").strip()
        if process.returncode != 0:
            error = f"worker exited with code {process.returncode}"
            if text:
                error = f"{error}: {text}"
            return WorkerResult(
                ok=False,
                mode=mode,
                error=error,
                error_type="WorkerExit",
                traceback=text or None,
            )
        try:
            return self._read_result(job)
        except _ResultError as exc:
            error = str(exc)
            if text:
                error = f"{error}: {text}"
            return WorkerResult(
                ok=False,
                mode=mode,
                error=error,
                error_type="WorkerError",
                traceback=text or None,
            )

    async def start(self, request: JobRequest) -> str:
        """Start an execute job in the background and return its id."""
        job = self._create(uuid.uuid4().hex, request)
        worker_request = WorkerRequest(
            mode="execute",
            log_dir=str(job.log_dir),
            **request.model_dump(exclude_unset=True),
        )
        self._write_request(job, worker_request)
        self._jobs[job.id] = job
        job.task = asyncio.create_task(self._supervise(job))
        return job.id

    async def cancel(self, job_id: str) -> JobStatus | None:
        """Kill the job's process group. Idempotent and safe for unknown ids."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job.state in TERMINAL_STATES:
            return self._status(job)
        job.state = "cancelled"
        job.ended = job.ended or _now()
        await self._terminate(job.process)
        return self._status(job)

    async def stream(
        self,
        job_id: str,
        *,
        start_index: int = 0,
    ) -> AsyncIterator[tuple[str, dict[str, Any], int | None]]:
        """Yield ``(event, data, event_id)`` tuples for the SSE endpoint."""
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)

        log_path: Path | None = None
        offset = 0
        buffer = b""
        index = 0
        last_state: str | None = None

        async def drain() -> list[dict[str, Any]]:
            nonlocal log_path, offset, buffer
            found = await asyncio.to_thread(_find_log, job.log_dir)
            if found is None:
                return []
            if found != log_path:
                log_path, offset, buffer = found, 0, b""
            records, offset, buffer = await asyncio.to_thread(_read_records, found, offset, buffer)
            return records

        while True:
            status = self._status(job)
            if status.state != last_state:
                last_state = status.state
                yield "status", {"state": status.state}, None

            for record in await drain():
                index += 1
                if index > start_index:
                    yield "log", {"record": record}, index

            if status.state in TERMINAL_STATES:
                for record in await drain():
                    index += 1
                    if index > start_index:
                        yield "log", {"record": record}, index
                data: dict[str, Any] = {"state": status.state}
                if status.result is not None:
                    data["result"] = status.result.model_dump(mode="json", by_alias=True)
                if status.error:
                    data["error"] = status.error
                yield "done", data, None
                return

            await asyncio.sleep(0.15)

    async def shutdown(self) -> None:
        """Cancel every unfinished job (used by tests and orderly shutdown)."""
        for job in list(self._jobs.values()):
            if job.state not in TERMINAL_STATES:
                await self.cancel(job.id)

    def _create(self, job_id: str, request: JobRequest) -> _Job:
        directory = self.project_root / ".seq_ext_gui" / "jobs" / job_id
        directory.mkdir(parents=True, exist_ok=True)
        log_dir = directory / "logs"
        log_dir.mkdir(exist_ok=True)
        return _Job(
            id=job_id,
            directory=directory,
            request_path=directory / "request.json",
            result_path=directory / "result.json",
            stderr_path=directory / "stderr.log",
            log_dir=log_dir,
        )

    @staticmethod
    def _write_request(job: _Job, request: WorkerRequest) -> None:
        job.request_path.write_text(
            request.model_dump_json(indent=2, exclude_unset=True), encoding="utf-8"
        )

    @staticmethod
    def _status(job: _Job) -> JobStatus:
        return JobStatus(
            id=job.id,
            state=job.state,  # type: ignore[arg-type]
            created=job.created,
            started=job.started,
            ended=job.ended,
            exit_code=job.exit_code,
            error=job.error,
            result=job.result,
            log_dir=str(job.log_dir),
        )

    async def _supervise(self, job: _Job) -> None:
        if job.state != "queued":
            return
        job.state = "running"
        job.started = _now()

        try:
            job.stderr_file = job.stderr_path.open("wb")
            job.process = await asyncio.create_subprocess_exec(
                *self.worker_cmd,
                str(job.request_path),
                str(job.result_path),
                cwd=str(self.project_root),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=job.stderr_file,
                start_new_session=True,
            )
        except OSError as exc:
            job.state = "failed"
            job.error = f"cannot start worker: {exc}"
            job.ended = _now()
            self._close_stderr(job)
            return

        if job.state == "cancelled":
            await self._terminate(job.process)
            job.exit_code = job.process.returncode
            job.ended = job.ended or _now()
            self._close_stderr(job)
            return

        try:
            job.exit_code = await asyncio.wait_for(job.process.wait(), timeout=self.timeout)
        except TimeoutError:
            await self._terminate(job.process)
            job.exit_code = job.process.returncode
            if job.state != "cancelled":
                job.state = "failed"
                job.error = f"job timed out after {self.timeout:g} s"
        except asyncio.CancelledError:
            await self._terminate(job.process)
            if job.state not in TERMINAL_STATES:
                job.state = "cancelled"
                job.ended = _now()
            self._close_stderr(job)
            raise
        finally:
            self._close_stderr(job)

        if job.state == "cancelled":
            job.ended = job.ended or _now()
            return
        if job.state != "failed":
            try:
                job.result = self._read_result(job)
            except _ResultError as exc:
                job.state = "failed"
                message = str(exc)
                if job.exit_code not in (None, 0):
                    message = f"{message} (worker exited with code {job.exit_code})"
                    tail = self._stderr_tail(job)
                    if tail:
                        message = f"{message}: {tail}"
                job.error = message
            else:
                if not job.result.ok:
                    job.state = "failed"
                    job.error = job.result.error or "worker reported failure"
                elif job.exit_code not in (None, 0):
                    job.state = "failed"
                    job.error = f"worker exited with code {job.exit_code}"
                else:
                    job.state = "succeeded"
        job.ended = _now()

    @staticmethod
    async def _terminate(process: asyncio.subprocess.Process | None) -> None:
        if process is None or process.returncode is not None:
            return
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except OSError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            await process.wait()
        except ProcessLookupError:
            pass

    @staticmethod
    def _read_result(job: _Job) -> WorkerResult:
        try:
            text = job.result_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise _ResultError("worker produced no result file") from exc
        except OSError as exc:
            raise _ResultError(f"cannot read worker result: {exc}") from exc
        if not text.strip():
            raise _ResultError("worker produced an empty result file")
        try:
            return WorkerResult.model_validate_json(text)
        except ValidationError as exc:
            raise _ResultError(f"invalid worker result: {exc}") from exc

    @staticmethod
    def _stderr_tail(job: _Job, limit: int = 2000) -> str:
        try:
            text = job.stderr_path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return ""
        return text[-limit:] if len(text) > limit else text

    @staticmethod
    def _close_stderr(job: _Job) -> None:
        if job.stderr_file is not None:
            try:
                job.stderr_file.close()
            except OSError:
                pass
            job.stderr_file = None


def _find_log(log_dir: Path) -> Path | None:
    paths = sorted(log_dir.glob("*.jsonl"))
    return paths[0] if paths else None


def _read_records(
    path: Path,
    offset: int,
    buffer: bytes,
) -> tuple[list[dict[str, Any]], int, bytes]:
    with path.open("rb") as handle:
        handle.seek(offset)
        chunk = handle.read()
        new_offset = handle.tell()
    lines = (buffer + chunk).split(b"\n")
    remainder = lines.pop()
    records: list[dict[str, Any]] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            records.append(json.loads(text))
        except (ValueError, UnicodeDecodeError):
            records.append({"raw": text.decode("utf-8", "replace")})
    return records, new_offset, remainder
