"""One-shot worker: request JSON in, result JSON out.

Invoked as ``python -m seq_ext_gui.worker <request.json> <result.json>``.
Exit code is 0 for handled flow errors (``ok=false`` in the result) and
non-zero only when the worker itself cannot produce a result.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from .contracts import WorkerRequest, WorkerResult
from .engine import discover, execute, plan


def _dispatch(request: WorkerRequest) -> WorkerResult:
    if request.mode == "execute":
        return execute(request)
    if request.mode == "discover":
        return discover(request)
    if request.mode == "plan":
        return plan(request)
    raise ValueError(f"unknown worker mode: {request.mode!r}")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: python -m seq_ext_gui.worker <request.json> <result.json>", file=sys.stderr)
        return 2

    request_path = Path(args[0])
    result_path = Path(args[1])
    mode = "plan"
    try:
        request = WorkerRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
        mode = request.mode
        result = _dispatch(request)
    except Exception as exc:
        traceback.print_exc()
        result = WorkerResult(
            ok=False,
            mode=mode,
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        _write(result_path, result)
        return 1

    _write(result_path, result)
    return 0


def _write(path: Path, result: WorkerResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(by_alias=True, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
