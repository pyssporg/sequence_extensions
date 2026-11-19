"""Headless run API: load a module, select a flow, gate the plan, run it.

One public unit behind both frontends.  The CLI (:mod:`flow_runner`) and the
GUI worker are thin adapters over :func:`run_flow`; neither re-derives module
loading, flow selection, the plan-schema gate, or run projection.

The engine's ``flow-plan/2`` document remains the only wire contract:
``run_flow`` either builds one with :func:`plan_document`, merges overrides
with :func:`apply_override`, or accepts a supplied document, and then runs it
with :func:`execute_plan`.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import importlib.util
import os
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from sequence_extensions.flow import (
    PLAN_SCHEMA,
    NodeFunction,
    Run,
    RunOptions,
    apply_override,
    execute_plan,
    jsonable,
    plan_document,
)

from ._discovery import find_nodes

__all__ = [
    "HeadlessRun",
    "load_flow_module",
    "require_plan_document",
    "run_flow",
    "select_flow",
]


@dataclass(frozen=True)
class HeadlessRun:
    """One headless unit's outcome: the selected flow, its plan, its run.

    ``run`` is ``None`` when the caller asked for the plan only.  ``to_dict``
    is the serializable projection both frontends can hand to their own wire
    formats.
    """

    flow_name: str
    document: dict
    run: Run | None

    def to_dict(self) -> dict:
        """Plain-data projection: ``{"flow_name", "plan", "run"}``."""
        return {
            "flow_name": self.flow_name,
            "plan": self.document,
            "run": _run_projection(self.run),
        }


# ---------------------------------------------------------------- #
# Module loading
# ---------------------------------------------------------------- #
def load_flow_module(source: str | Path) -> ModuleType:
    """Import a flow module from a dotted name, a ``.py`` file, or a directory.

    A dotted name is imported normally.  A ``.py`` file is loaded by path under
    a synthetic module name derived from its resolved path.  A directory is
    imported as a package with its parent on ``sys.path``.

    Raises ``ValueError`` for a non-``.py`` file, ``FileNotFoundError`` for a
    missing path, and ``ImportError`` when the import itself fails.
    """
    if isinstance(source, Path) or _looks_like_path(str(source)):
        return _load_path(source)

    try:
        return importlib.import_module(str(source))
    except Exception as exc:
        raise ImportError(f"cannot import module {str(source)!r}: {exc}") from None


def _looks_like_path(text: str) -> bool:
    """A string is a path when it exists, ends in ``.py``, or has a separator."""
    return text.endswith(".py") or os.sep in text or "/" in text or Path(text).exists()


def _load_path(source: str | Path) -> ModuleType:
    path = Path(source).expanduser().resolve()
    label = str(source)
    if not path.exists():
        raise FileNotFoundError(f"cannot import module {label!r}: flow module not found: {path}")
    if path.is_dir():
        return _import_directory(path, label)
    if path.suffix != ".py":
        raise ValueError(f"cannot import module {label!r}: flow file must be a .py file: {path}")
    return _import_file(path, label)


def _import_directory(path: Path, label: str) -> ModuleType:
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    importlib.invalidate_caches()
    try:
        return importlib.import_module(path.name)
    except Exception as exc:
        raise ImportError(f"cannot import module {label!r}: {exc}") from None


def _import_file(path: Path, label: str) -> ModuleType:
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    importlib.invalidate_caches()

    # A stable synthetic name derived from the resolved path; registered before
    # exec so dataclasses and pickle can find the module by name.
    name = "_flow_runner_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import module {label!r}: cannot load Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(name, None)
        raise ImportError(f"cannot import module {label!r}: {exc}") from None
    return module


# ---------------------------------------------------------------- #
# Selection and the schema gate
# ---------------------------------------------------------------- #
def select_flow(module: ModuleType, name: str | None = None) -> tuple[str, NodeFunction]:
    """Return the root node to run: the only one, or the exact ``name``.

    Raises ``ValueError`` when no name is given and the module does not define
    exactly one node, or when ``name`` does not match a node.
    """
    nodes = find_nodes(module)
    available = sorted(nodes)

    if name is None:
        if len(nodes) != 1:
            raise _selection_error(
                f"no flow selected; {len(available)} available: {_names(available)}",
                available,
            )
        flow_name, fn = next(iter(nodes.items()))
        return flow_name, fn

    fn = nodes.get(name)
    if fn is None:
        module_name = getattr(module, "__name__", module)
        raise _selection_error(
            f"no flow {name!r} in module {module_name!r}; available: {_names(available)}",
            available,
        )
    return name, fn


def require_plan_document(document: Any) -> dict:
    """Return ``document`` unchanged when it carries the ``flow-plan/2`` marker."""
    schema = document.get("schema") if isinstance(document, dict) else None
    if schema != PLAN_SCHEMA:
        raise ValueError(f"expected schema {PLAN_SCHEMA!r}, got {schema!r}")
    return document


# ---------------------------------------------------------------- #
# The run unit
# ---------------------------------------------------------------- #
def run_flow(
    source: ModuleType | str | Path,
    *,
    flow_name: str | None = None,
    document: dict | None = None,
    seed: Mapping[str, Any] | None = None,
    overrides: Iterable[dict] = (),
    options: RunOptions | None = None,
    log: str | Path | None = None,
    cwd: str | Path | None = None,
    plan_only: bool = False,
) -> HeadlessRun:
    """Load, select, gate, plan/override, and (unless ``plan_only``) execute.

    ``source`` may be an already-loaded module, which is then not re-imported;
    callers that must inspect the signature before planning pass the module
    they already loaded.  ``cwd`` is process-global: it is entered around load,
    plan, and execute and the previous directory is restored even when an
    exception escapes.
    """
    with _working_directory(cwd):
        module = source if isinstance(source, ModuleType) else load_flow_module(source)
        selected, node = select_flow(module, flow_name)
        try:
            if document is None:
                document = plan_document(node, **dict(seed or {}))
            for override in overrides:
                document = apply_override(document, override)
            document = require_plan_document(document)
            if plan_only:
                return HeadlessRun(flow_name=selected, document=document, run=None)
            run = execute_plan(node, document, options=options, log=log)
        except Exception as exc:
            if getattr(exc, "flow_name", None) is None:
                exc.flow_name = selected
            raise
        return HeadlessRun(flow_name=selected, document=document, run=run)


# ---------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------- #
@contextlib.contextmanager
def _working_directory(cwd: str | Path | None):
    if cwd is None:
        yield
        return
    previous = Path.cwd()
    os.chdir(cwd)
    try:
        yield
    finally:
        os.chdir(previous)


def _names(available: list[str]) -> str:
    return ", ".join(available) if available else "none"


def _selection_error(message: str, available: list[str]) -> ValueError:
    error = ValueError(message)
    error.available_flows = list(available)
    return error


def _run_projection(run: Run | None) -> dict | None:
    if run is None:
        return None
    error = run.error
    return {
        "status": run.status,
        "result": jsonable(run.result),
        "run_id": run.run_id,
        "node": run.node,
        "duration_ms": run.duration_ms,
        "attempt": run.attempt,
        "started": run.started,
        "ended": run.ended,
        "log": str(run.log) if run.log is not None else None,
        "error": str(error) if error is not None else None,
        "failed_nodes": [list(path) for path in run.failed_nodes],
    }
