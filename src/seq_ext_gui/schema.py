"""Validate ``flow-plan/2`` documents against the engine's normative schema.

The engine owns the schema.  This module loads the checked-in artifact from
the installed ``sequence_extensions`` package and falls back to the engine's
``plan_schema()`` accessor for older builds.  Nothing here runs at import time
beyond defining the lazy accessors, so a stale engine is reported only when a
plan is actually validated.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

SCHEMA_PACKAGE = "sequence_extensions"
SCHEMA_PATH = ("schemas", "flow-plan-2.schema.json")
_MAX_ERRORS = 5

_INSTALL_HINT = (
    "the installed sequence_extensions does not expose the flow-plan/2 JSON "
    "Schema; install a build that ships schemas/flow-plan-2.schema.json or "
    "exports sequence_extensions.flow.plan_schema()"
)


class PlanValidationError(ValueError):
    """A plan document does not satisfy the engine's ``flow-plan/2`` schema."""

    def __init__(self, errors: list[ValidationError]) -> None:
        self.errors = list(errors)
        super().__init__(_format_errors(self.errors))


def validate_plan(document: Any) -> None:
    """Raise :class:`PlanValidationError` unless *document* is a valid plan."""
    errors = sorted(
        _validator().iter_errors(document),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        raise PlanValidationError(errors)


def is_complete_document(document: Any) -> bool:
    """True when *document* carries every key a fully emitted plan carries.

    Partial seeds are a supported import format; they are validated only after
    the engine has re-planned them into a full document.
    """
    if not isinstance(document, dict):
        return False
    schema = _schema()
    required = schema.get("required", ())
    if not set(required) <= document.keys():
        return False
    options = document.get("options")
    if not isinstance(options, dict):
        return False
    option_keys = schema["$defs"]["options"].get("properties", {})
    return set(option_keys) <= options.keys()


@lru_cache(maxsize=1)
def _schema() -> dict[str, Any]:
    """Load the engine's schema artifact once, falling back to ``plan_schema``."""
    artifact = _read_artifact()
    if artifact is not None:
        return artifact
    try:
        from sequence_extensions.flow import plan_schema
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(_INSTALL_HINT) from exc
    return plan_schema()


def _read_artifact() -> dict[str, Any] | None:
    """Return the checked-in schema artifact, or ``None`` when it is absent."""
    try:
        artifact = resources.files(SCHEMA_PACKAGE)
        for part in SCHEMA_PATH:
            artifact = artifact.joinpath(part)
        if not artifact.is_file():
            return None
        return json.loads(artifact.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError, OSError, TypeError):
        return None


@lru_cache(maxsize=1)
def option_defaults() -> dict[str, Any]:
    """Engine defaults for every plan option, keyed in schema order."""
    from sequence_extensions.flow import RunOptions

    resolved = RunOptions().resolve("plan")
    keys = _schema()["$defs"]["options"].get("properties", {})
    return {key: getattr(resolved, key) for key in keys}


@lru_cache(maxsize=1)
def policy_defaults() -> dict[str, Any]:
    """Engine defaults for every node-policy field, keyed in schema order."""
    from sequence_extensions.flow import NodePolicy

    defaults = NodePolicy()
    keys = _schema()["$defs"]["policy"].get("properties", {})
    return {key: getattr(defaults, key) for key in keys}


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    """Lazily build and cache the one validator used for every check."""
    return Draft202012Validator(_schema())


def _format_errors(errors: list[ValidationError]) -> str:
    shown = errors[:_MAX_ERRORS]
    lines = [f"{_path(error)}: {error.message}" for error in shown]
    if len(errors) > len(shown):
        lines.append(f"... and {len(errors) - len(shown)} more error(s)")
    return "invalid flow-plan/2 document:\n" + "\n".join(lines)


def _path(error: ValidationError) -> str:
    parts = ["data"]
    for part in error.absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    return "".join(parts)
