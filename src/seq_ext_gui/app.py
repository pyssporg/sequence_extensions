"""FastAPI application: project files, worker evaluation, jobs, and SSE."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .contracts import (
    FileContent,
    HealthResponse,
    JobRequest,
    JobStatus,
    RootRequest,
    TreeResponse,
    WorkerResult,
)
from .files import ProjectFiles
from .jobs import JobManager

STATIC_DIR = Path(__file__).resolve().parent / "static"
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _format_sse(event: str, data: dict[str, Any], event_id: int | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"


def _confined_job(files: ProjectFiles, payload: JobRequest) -> JobRequest:
    # model_copy keeps ``model_fields_set`` so the worker can tell an absent
    # optional field from one explicitly set to None.
    return payload.model_copy(update={"flow_file": str(files.resolve(payload.flow_file))})


def _parse_last_event_id(request: Request) -> int:
    raw = request.headers.get("last-event-id", "")
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def create_app(
    project_root: Path,
    *,
    worker_cmd: list[str] | None = None,
    evaluate_timeout: float = 120.0,
    job_timeout: float = 600.0,
) -> FastAPI:
    root = Path(project_root).expanduser().resolve()
    files = ProjectFiles(root)
    jobs = JobManager(
        root,
        worker_cmd=worker_cmd,
        evaluate_timeout=evaluate_timeout,
        job_timeout=job_timeout,
    )

    @asynccontextmanager
    async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await jobs.shutdown()

    app = FastAPI(title="sequence_extensions GUI", version=__version__, lifespan=_lifespan)

    @app.middleware("http")
    async def _no_cache_static(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers.update(NO_CACHE_HEADERS)
        return response

    @app.exception_handler(ValueError)
    async def _value_error(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=__version__, project_root=str(files.root))

    @app.put("/api/root", response_model=HealthResponse)
    def set_root(payload: RootRequest) -> HealthResponse:
        """Switch the active project root; jobs created later use the new root."""
        target = Path(payload.path).expanduser()
        if not target.is_absolute():
            raise ValueError("project root must be an absolute path")
        if not target.is_dir():
            raise ValueError(f"not a directory: {payload.path}")
        resolved = target.resolve()
        files.set_root(resolved)
        jobs.set_root(resolved)
        return HealthResponse(version=__version__, project_root=str(resolved))

    @app.get("/api/tree", response_model=TreeResponse)
    def tree(path: str = "") -> TreeResponse:
        return files.tree(path)

    @app.get("/api/file", response_model=FileContent)
    def read_file(path: str) -> FileContent:
        return files.read(path)

    @app.post("/api/evaluate", response_model=WorkerResult)
    async def evaluate(payload: JobRequest) -> WorkerResult:
        return await jobs.evaluate(_confined_job(files, payload))

    @app.post("/api/discover", response_model=WorkerResult)
    async def discover(payload: JobRequest) -> WorkerResult:
        return await jobs.discover(_confined_job(files, payload))

    @app.post("/api/execute")
    async def execute(payload: JobRequest) -> dict[str, str]:
        job_id = await jobs.start(_confined_job(files, payload))
        return {"job_id": job_id}

    def status_or_404(job_id: str) -> JobStatus:
        status = jobs.status(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
        return status

    @app.get("/api/jobs/{job_id}", response_model=JobStatus)
    def job_status(job_id: str) -> JobStatus:
        return status_or_404(job_id)

    @app.get("/api/jobs/{job_id}/events")
    async def job_events(job_id: str, request: Request) -> StreamingResponse:
        status_or_404(job_id)
        start_index = _parse_last_event_id(request)

        async def stream() -> AsyncIterator[str]:
            async for event, data, event_id in jobs.stream(job_id, start_index=start_index):
                yield _format_sse(event, data, event_id)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={**NO_CACHE_HEADERS, "X-Accel-Buffering": "no"},
        )

    @app.post("/api/jobs/{job_id}/cancel", response_model=JobStatus)
    async def cancel_job(job_id: str) -> JobStatus:
        status = await jobs.cancel(job_id)
        if status is None:
            raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
        return status

    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> Response:
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            return JSONResponse({"detail": "static UI is not installed"}, status_code=404)
        return FileResponse(
            index_path,
            media_type="text/html",
            headers=NO_CACHE_HEADERS,
        )

    return app
