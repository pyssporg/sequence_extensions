"""Plan and execute a flow module inside the worker process.

The only configuration artifact is the engine's ``flow-plan/2`` JSON document.
This module imports ``sequence_extensions`` and user flow code; the web process
talks to it through :mod:`seq_ext_gui.worker`.
"""

from __future__ import annotations

import contextlib
import inspect
import json
import math
import time
import traceback
from pathlib import Path
from typing import Any

from sequence_extensions.flow import (
    NodeFunction,
    RunOptions,
    apply_override,
)
from sequence_extensions.flow_runner import find_nodes
from sequence_extensions.flow_runner.headless import (
    HeadlessRun,
    load_flow_module,
    require_plan_document,
    run_flow,
    select_flow,
)

from .contracts import (
    PLAN_SCHEMA,
    NodeCard,
    ParamSpec,
    RunResult,
    WorkerRequest,
    WorkerResult,
    annotate_param,
    decode_value,
    encode_value,
    to_document,
)
from .schema import is_complete_document, validate_plan


class EngineError(ValueError):
    """A handled config/flow error that becomes ``ok=false``."""

    def __init__(self, message: str, *, available_flows: list[str] | None = None) -> None:
        super().__init__(message)
        self.available_flows = list(available_flows or [])


def plan(request: WorkerRequest) -> WorkerResult:
    """Build the wire plan for ``request`` without executing user node bodies."""
    started = time.monotonic()
    try:
        seed = request.plan
        if seed is not None:
            require_plan_document(seed)
            if is_complete_document(seed):
                validate_plan(seed)
        flow_file = Path(request.flow_file).expanduser().resolve()
        module = load_flow_module(flow_file)
        selected, fn = select_flow(module, request.flow_name)
        available = sorted(find_nodes(module))
        root_kwargs = _root_values(fn, seed)
        fresh = run_flow(
            module,
            flow_name=selected,
            seed=root_kwargs,
            cwd=flow_file.parent,
            plan_only=True,
        ).document
        document = fresh
        warnings: list[str] = []
        if seed is not None:
            override, seed_warnings = _override_from_seed(seed, fresh, root_kwargs)
            warnings.extend(seed_warnings)
            raw_options = seed.get("options")
            if raw_options:
                _run_options(seed)  # validate through the engine's RunOptions
                override["options"] = dict(raw_options)
            if override:
                document = apply_override(fresh, override)
        validate_plan(document)
        wire_plan, wire_warnings = _wire_plan(fresh, values=document)
        warnings.extend(wire_warnings)
        return WorkerResult(
            ok=True,
            mode="plan",
            flow_name=selected,
            available_flows=available,
            plan=wire_plan,
            warnings=warnings,
            duration_ms=_elapsed_ms(started),
        )
    except Exception as exc:
        return _error_result(request, exc, started, "plan")


def discover(request: WorkerRequest) -> WorkerResult:
    """List every ``@node`` in the flow module without running node bodies."""
    started = time.monotonic()
    try:
        flow_file = Path(request.flow_file).expanduser().resolve()
        with contextlib.chdir(flow_file.parent):
            module = load_flow_module(flow_file)
            cards = [_node_card(name, node) for name, node in find_nodes(module).items()]
        return WorkerResult(
            ok=True,
            mode="discover",
            nodes=cards,
            duration_ms=_elapsed_ms(started),
        )
    except Exception as exc:
        return _error_result(request, exc, started, "discover")


def execute(request: WorkerRequest) -> WorkerResult:
    """Run the request's plan document.  Flow failures are ``ok=false``."""
    started = time.monotonic()
    try:
        if request.plan is None:
            raise EngineError("execute requires a plan")
        document = to_document(request.plan)
        require_plan_document(document)
        validate_plan(document)
        flow_file = Path(request.flow_file).expanduser().resolve()
        try:
            outcome = run_flow(
                flow_file,
                flow_name=request.flow_name,
                document=document,
                log=request.log_dir,
                cwd=flow_file.parent,
            )
        except Exception as exc:
            wire_plan, warnings = _wire_plan(document)
            run = getattr(exc, "run", None)
            projected = HeadlessRun("", document, run).to_dict()["run"] if run is not None else None
            run_result = (
                RunResult(**projected)
                if projected is not None
                else RunResult(status="error", error=str(exc), error_type=type(exc).__name__)
            )
            return WorkerResult(
                ok=False,
                mode="execute",
                flow_name=getattr(exc, "flow_name", None) or request.flow_name,
                plan=wire_plan,
                run=run_result,
                warnings=warnings,
                error=str(exc),
                error_type=type(exc).__name__,
                traceback=traceback.format_exc(),
                duration_ms=_elapsed_ms(started),
            )
        wire_plan, warnings = _wire_plan(document)
        return WorkerResult(
            ok=True,
            mode="execute",
            flow_name=outcome.flow_name,
            plan=wire_plan,
            run=RunResult(**outcome.to_dict()["run"]),
            warnings=warnings,
            duration_ms=_elapsed_ms(started),
        )
    except Exception as exc:
        return _error_result(request, exc, started, "execute")


# ---------------------------------------------------------------- #
# Plan-document seeding
# ---------------------------------------------------------------- #
def _run_options(document: dict[str, Any] | None) -> RunOptions:
    raw = (document or {}).get("options") or {}
    return RunOptions(**raw)


def _root_values(fn: NodeFunction, document: dict[str, Any] | None) -> dict[str, Any]:
    """Decode root parameters from the seed document into keyword arguments."""
    signature = inspect.signature(fn.fn)
    params = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in {parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY}
    ]
    types = {parameter.name: _annotation_name(parameter.annotation) for parameter in params}
    values: dict[str, Any] = {}
    unknown: list[str] = []
    for entry in (document or {}).get("parameters", ()):
        name = entry.get("name")
        if name not in types:
            if name is not None:
                unknown.append(name)
            continue
        value = entry.get("value")
        if value is not None:
            values[name] = decode_value(value, types[name])
    if unknown:
        listed = ", ".join(sorted(repr(name) for name in unknown))
        raise EngineError(f"unknown root parameter(s): {listed}")

    missing = [
        parameter.name
        for parameter in params
        if parameter.default is inspect.Parameter.empty and parameter.name not in values
    ]
    if missing:
        raise EngineError("missing required root parameter(s): " + ", ".join(missing))
    return values


def _override_from_seed(
    seed: dict[str, Any], fresh: dict[str, Any], root_kwargs: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Re-apply the seed plan's edits on top of the freshly planned document.

    Node edits target one occurrence by exact identity ``(name, path,
    instance)``.  A seed node without that identity (a legacy plan) or with an
    identity the fresh plan no longer contains is skipped with a warning;
    there is no name-wide fallback.  Only values that differ from the fresh
    plan are emitted, so unchanged defaults are not pinned.  Root parameters
    keep their existing name-keyed behavior.
    """
    override: dict[str, Any] = {}
    warnings: list[str] = []
    if root_kwargs:
        override["parameters"] = [
            {"name": name, "value": value} for name, value in root_kwargs.items()
        ]

    fresh_by_identity = {
        (entry["name"], tuple(entry.get("path", ())), entry.get("instance", 1)): entry
        for entry in fresh.get("nodes", ())
    }

    node_overrides: list[dict[str, Any]] = []
    for entry in seed.get("nodes", ()):
        name = entry.get("name")
        if name is None:
            continue
        if "path" not in entry or "instance" not in entry:
            warnings.append(
                f"node {name} has no identity in the imported plan; "
                "its edits were skipped; re-Evaluate to edit it"
            )
            continue

        path = list(entry.get("path") or ())
        instance = entry["instance"]
        target = fresh_by_identity.get((name, tuple(path), instance))
        if target is None:
            warnings.append(
                f"node {name} #{instance} no longer exists in the re-planned flow; "
                "re-Evaluate to edit it"
            )
            continue

        fresh_params = {param["name"]: param for param in target.get("params", ())}
        params = []
        for param in entry.get("params", ()):
            param_name = param.get("name")
            fresh_param = fresh_params.get(param_name)
            if fresh_param is None:
                warnings.append(
                    f"parameter {param_name} on node {name} #{instance} no longer "
                    "exists in the re-planned flow; skipped"
                )
                continue
            value = decode_value(param.get("value"), fresh_param.get("type", ""))
            if value != fresh_param.get("value"):
                params.append({"name": param_name, "value": value})

        spec: dict[str, Any] = {"name": name, "path": path, "instance": instance}
        if params:
            spec["params"] = params

        policy = entry.get("policy")
        if isinstance(policy, dict):
            fresh_policy = target.get("policy") or {}
            changed_policy = {
                field: policy[field]
                for field in fresh_policy
                if field in policy and policy[field] != fresh_policy[field]
            }
            if changed_policy:
                spec["policy"] = changed_policy

        if "params" in spec or "policy" in spec:
            node_overrides.append(spec)

    if node_overrides:
        override["nodes"] = node_overrides
    return override, warnings


def _node_card(name: str, node: Any) -> NodeCard:
    doc = (inspect.getdoc(node) or "").strip()
    summary = doc.splitlines()[0] if doc else ""
    wrapped = getattr(node, "fn", node)
    return NodeCard(
        name=name,
        summary=summary,
        signature=_signature_preview(wrapped),
        params=_param_specs(wrapped),
    )


def _param_specs(fn: Any) -> list[ParamSpec]:
    """Describe the root parameters discovery exposes, by signature only."""
    signature = inspect.signature(fn)
    return [
        _param_spec(parameter)
        for parameter in signature.parameters.values()
        if parameter.kind in {parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY}
    ]


def _param_spec(parameter: inspect.Parameter) -> ParamSpec:
    default, note = _display_default(parameter.default)
    return ParamSpec(
        name=parameter.name,
        type=_annotation_name(parameter.annotation),
        required=parameter.default is inspect.Parameter.empty,
        default=default,
        default_note=note,
    )


def _display_default(value: Any) -> tuple[Any, str | None]:
    """Return a JSON-safe default and an optional note explaining a lossy one."""
    if value is inspect.Parameter.empty:
        return None, None
    if isinstance(value, Path):
        return str(value), None
    if isinstance(value, bool | int | str):
        return value, None
    if isinstance(value, float):
        if math.isfinite(value):
            return value, None
        return repr(value), "non-finite float"
    if isinstance(value, list | tuple | dict):
        try:
            return json.loads(json.dumps(value)), None
        except (TypeError, ValueError):
            return None, f"unsupported value type: {type(value).__name__}"
    return None, f"unsupported value type: {type(value).__name__}"


def _signature_preview(fn: Any) -> str:
    """Render ``inspect.signature`` using readable annotation names."""
    signature = inspect.signature(fn)
    parameters = list(signature.parameters.values())
    rendered: list[str] = []
    keyword_only_marker = False
    positional_only_marker = False

    for index, parameter in enumerate(parameters):
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY and not keyword_only_marker:
            if not any(
                earlier.kind is inspect.Parameter.VAR_POSITIONAL for earlier in parameters[:index]
            ):
                rendered.append("*")
            keyword_only_marker = True

        prefix = ""
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            prefix = "*"
        elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
            prefix = "**"
        text = prefix + parameter.name
        annotation = _annotation_name(parameter.annotation)
        if annotation:
            text += f": {annotation}"
        if parameter.default is not inspect.Parameter.empty:
            text += f" = {parameter.default!r}"
        rendered.append(text)

        if (
            parameter.kind is inspect.Parameter.POSITIONAL_ONLY
            and not positional_only_marker
            and (
                index + 1 == len(parameters)
                or parameters[index + 1].kind is not inspect.Parameter.POSITIONAL_ONLY
            )
        ):
            rendered.append("/")
            positional_only_marker = True

    preview = f"({', '.join(rendered)})"
    returns = _annotation_name(signature.return_annotation)
    return f"{preview} -> {returns}" if returns else preview


def _annotation_name(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return ""
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation))


# ---------------------------------------------------------------- #
# Wire plan and the documented editability heuristic
# ---------------------------------------------------------------- #
def _wire_plan(
    document: dict[str, Any], *, values: dict[str, Any] | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Annotate ``document`` for the wire, taking values from ``values``."""
    warnings: list[str] = []
    value_document = values if values is not None else document
    value_parameters = {
        param["name"]: param.get("value") for param in value_document.get("parameters", ())
    }
    value_nodes = value_document.get("nodes", ())

    nodes: list[dict[str, Any]] = []

    for index, entry in enumerate(document.get("nodes", ())):
        value_entry = value_nodes[index] if index < len(value_nodes) else entry
        value_params = {
            param["name"]: param.get("value") for param in value_entry.get("params", ())
        }
        params = []
        if entry.get("kind") != "gather":
            for raw in entry.get("params", ()):
                params.append(_node_param(raw, value_params.get(raw["name"], raw.get("value"))))
        nodes.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "kind": entry.get("kind", "node"),
                "path": list(entry.get("path", ())),
                "instance": entry.get("instance", 1),
                "policy": dict(value_entry.get("policy") or {}),
                "params": params,
            }
        )

    wire_plan = {
        "schema": value_document.get("schema", PLAN_SCHEMA),
        "parameters": [
            _root_param(raw, value_parameters.get(raw["name"], raw.get("value")))
            for raw in document.get("parameters", ())
        ],
        "nodes": nodes,
        "edges": [
            {"from": edge.get("from", edge.get("source")), "to": edge.get("to", edge.get("target"))}
            for edge in document.get("edges", ())
        ],
        "options": dict(value_document.get("options") or {}),
    }
    return wire_plan, warnings


def _root_param(raw: dict[str, Any], value: Any) -> dict[str, Any]:
    encoded, _editable, note = encode_value(value)
    default, _default_editable, _default_note = encode_value(raw.get("default"))
    return annotate_param(
        {
            "name": raw["name"],
            "type": raw.get("type", ""),
            "required": bool(raw.get("required")),
            "default": default,
            "value": encoded,
        },
        editable=True,
        note=note,
    )


def _node_param(raw: dict[str, Any], value: Any) -> dict[str, Any]:
    encoded, encodable, encodable_note = encode_value(value)
    default, _default_editable, _default_note = encode_value(raw.get("default"))
    required = bool(raw.get("required"))
    # Editability comes from the freshly planned code values, not from an
    # imported edit: an edited-but-re-evaluated parameter stays editable.
    code_value = raw.get("value")

    if not encodable:
        editable, note = False, encodable_note
    elif required and code_value is not None:
        editable, note = False, "set by flow code"
    elif not required and code_value == raw.get("default"):
        editable, note = True, None
    elif code_value != raw.get("default"):
        editable, note = False, "possibly set by flow code"
    else:
        editable, note = True, None

    return annotate_param(
        {
            "name": raw["name"],
            "type": raw.get("type", ""),
            "required": required,
            "default": default,
            "value": encoded,
        },
        editable=editable,
        note=note,
    )


def _error_result(
    request: WorkerRequest, exc: Exception, started: float, mode: str
) -> WorkerResult:
    return WorkerResult(
        ok=False,
        mode=mode,
        flow_name=getattr(exc, "flow_name", None) or request.flow_name,
        available_flows=list(getattr(exc, "available_flows", [])),
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc(),
        duration_ms=_elapsed_ms(started),
    )


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
