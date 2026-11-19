"""Command-line entry point for the local GUI server."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from .app import create_app

ENV_PROJECT_ROOT = "SEQ_EXT_GUI_PROJECT_ROOT"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="seq-ext-gui",
        description="Local web GUI for sequence_extensions flows.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="bind port (default: 8765)")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=f"project root (default: ${ENV_PROJECT_ROOT} or the current directory)",
    )
    args = parser.parse_args(argv)

    configured = args.project_root or os.environ.get(ENV_PROJECT_ROOT)
    root = Path(configured).expanduser() if configured else Path.cwd()
    root = root.resolve()
    if not root.is_dir():
        parser.error(f"project root is not a directory: {root}")

    uvicorn.run(create_app(root), host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
