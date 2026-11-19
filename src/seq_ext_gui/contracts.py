"""Wire models shared by the HTTP API and the worker subprocess.

Everything that crosses a process boundary is defined here exactly once.  The
configuration artifact is the engine's ``flow-plan/2`` JSON document: the GUI
imports and exports it as plain dicts, and the worker consumes it verbatim.
The engine's JSON Schema, not a Python mirror, defines its shape.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sequence_extensions.flow import PLAN_SCHEMA, jsonable

from .schema import option_defaults, policy_defaults

#: Keys the GUI adds to engine parameters for presentation only.
GUI_PARAM_KEYS = frozenset({"editable", "note"})


def annotate_param(
    param: dict[str, Any], *, editable: bool = True, note: str | None = None
) -> dict[str, Any]:
    """Return *param* plus the GUI's display-only annotations."""
    annotated = dict(param)
    annotated["editable"] = bool(editable)
    annotated["note"] = note
    return annotated


def to_document(plan_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a deep copy of *plan_dict* with GUI-only annotations stripped."""
    document = copy.deepcopy(plan_dict)
    document["parameters"] = [_strip_param(param) for param in document.get("parameters", ())]
    document["nodes"] = [
        {**node, "params": [_strip_param(param) for param in node.get("params", ())]}
        for node in document.get("nodes", ())
    ]
    return document


def _strip_param(param: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in param.items() if key not in GUI_PARAM_KEYS}


def _normalise_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Fill the defaults the old wire model supplied, keeping key order."""
    document = copy.deepcopy(plan)
    document.setdefault("schema", PLAN_SCHEMA)
    document["parameters"] = [_normalise_param(param) for param in document.get("parameters") or ()]
    document["nodes"] = [_normalise_node(node) for node in document.get("nodes") or ()]
    document["edges"] = [
        {
            "from": edge.get("from", edge.get("source")),
            "to": edge.get("to", edge.get("target")),
        }
        for edge in document.get("edges") or ()
    ]
    raw_options = document.get("options") or {}
    document["options"] = {
        key: raw_options.get(key, default) for key, default in option_defaults().items()
    }
    return document


def _normalise_param(param: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": param.get("name"),
        "type": param.get("type", ""),
        "required": param.get("required", False),
        "default": param.get("default"),
        "value": param.get("value"),
        "editable": param.get("editable", True),
        "note": param.get("note"),
    }


def _normalise_node(node: dict[str, Any]) -> dict[str, Any]:
    raw_policy = node.get("policy") or {}
    return {
        "id": node.get("id"),
        "name": node.get("name"),
        "kind": node.get("kind", "node"),
        "path": list(node.get("path") or ()),
        "instance": node.get("instance", 1),
        "policy": {key: raw_policy.get(key, default) for key, default in policy_defaults().items()},
        "params": [_normalise_param(param) for param in node.get("params") or ()],
    }


class ParamSpec(BaseModel):
    """One root parameter of a ``@node`` as discovery reports it."""

    name: str
    type: str = ""
    required: bool = False
    default: Any = None
    default_note: str | None = None


class JobRequest(BaseModel):
    flow_file: str
    flow_name: str | None = None
    plan: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class WorkerRequest(JobRequest):
    mode: Literal["plan", "execute", "discover"]
    log_dir: str | None = None


class RunResult(BaseModel):
    status: str
    result: Any = None
    run_id: str = ""
    node: str = ""
    duration_ms: int = 0
    attempt: int = 1
    started: str = ""
    ended: str = ""
    log: str | None = None
    error: str | None = None
    error_type: str | None = None
    failed_nodes: list[list[str]] = Field(default_factory=list)


class NodeCard(BaseModel):
    """One ``@node`` as the discovery view reports it."""

    name: str
    summary: str = ""
    signature: str = ""
    params: list[ParamSpec] = Field(default_factory=list)


class WorkerResult(BaseModel):
    ok: bool
    mode: str = "plan"
    flow_name: str | None = None
    available_flows: list[str] = Field(default_factory=list)
    nodes: list[NodeCard] = Field(default_factory=list)
    plan: dict[str, Any] | None = None
    run: RunResult | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    error_type: str | None = None
    traceback: str | None = None
    duration_ms: int = 0

    @field_validator("plan", mode="before")
    @classmethod
    def _plan_is_a_mapping(cls, value: Any) -> Any:
        if value is not None and not isinstance(value, dict):
            raise ValueError("plan must be a JSON object")
        return None if value is None else _normalise_plan(value)


class JobStatus(BaseModel):
    id: str
    state: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    created: str
    started: str | None = None
    ended: str | None = None
    exit_code: int | None = None
    error: str | None = None
    result: WorkerResult | None = None
    log_dir: str | None = None


class FileEntry(BaseModel):
    path: str
    name: str
    kind: Literal["dir", "file"]
    size: int | None = None
    mtime: float | None = None


class TreeResponse(BaseModel):
    root: str
    path: str
    entries: list[FileEntry] = Field(default_factory=list)


class FileContent(BaseModel):
    path: str
    content: str


class HealthResponse(BaseModel):
    ok: bool = True
    version: str
    project_root: str


class RootRequest(BaseModel):
    """An absolute directory to make the active project root."""

    path: str


def encode_value(value: Any) -> tuple[Any, bool, str | None]:
    """Return ``(json_value, editable, note)`` for a raw Python value.

    ``Path`` follows the engine's JSON-safe ``jsonable`` form (``{"path": ...,
    "sha256": ...}``) so an exported plan can be decoded by ``execute_plan``.
    """
    if isinstance(value, Path):
        return jsonable(value), True, None
    if value is None or isinstance(value, bool | int | float | str):
        return value, True, None
    if isinstance(value, list | tuple | dict):
        try:
            return json.loads(json.dumps(value)), True, None
        except (TypeError, ValueError):
            return None, False, f"unsupported value type: {type(value).__name__}"
    return None, False, f"unsupported value type: {type(value).__name__}"


def decode_value(value: Any, type_hint: str) -> Any:
    """Coerce a JSON value back to the Python type named by ``type_hint``."""
    hint = (type_hint or "").strip()
    if hint.endswith("Path") and value is not None:
        if isinstance(value, dict):
            raw = value.get("path")
            if raw is None:
                raise ValueError(f"cannot read {value!r} as Path")
            value = raw
        return Path(str(value)).expanduser()
    if hint in {"int", "float", "str", "bool"} and isinstance(value, str):
        text = value.strip()
        if hint == "int":
            return int(text)
        if hint == "float":
            return float(text)
        if hint == "bool":
            lowered = text.lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no", ""}:
                return False
            raise ValueError(f"cannot read {value!r} as bool")
        return text
    return value
