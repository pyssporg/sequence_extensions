"""Tests for validating plan documents against the engine's JSON Schema."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from seq_ext_gui import schema
from seq_ext_gui.schema import PlanValidationError, validate_plan
from sequence_extensions.flow import plan_schema


def _invalid(document: dict[str, Any]) -> str:
    with pytest.raises(PlanValidationError) as caught:
        validate_plan(document)
    return str(caught.value)


def test_a_valid_engine_plan_passes(sample_plan: dict[str, Any]) -> None:
    assert "editable" not in sample_plan["parameters"][0]
    validate_plan(sample_plan)


def test_wrong_schema_const_is_rejected(sample_plan: dict[str, Any]) -> None:
    document = copy.deepcopy(sample_plan)
    document["schema"] = "flow-plan/1"

    message = _invalid(document)

    assert "data.schema" in message
    assert "flow-plan/2" in message


def test_missing_required_key_is_rejected(sample_plan: dict[str, Any]) -> None:
    document = copy.deepcopy(sample_plan)
    del document["nodes"]

    message = _invalid(document)

    assert "nodes" in message
    assert "required" in message


def test_unknown_node_key_is_rejected(sample_plan: dict[str, Any]) -> None:
    document = copy.deepcopy(sample_plan)
    document["nodes"][0]["bogus"] = 1

    message = _invalid(document)

    assert "data.nodes[0]" in message
    assert "bogus" in message


def test_error_message_names_the_offending_path(sample_plan: dict[str, Any]) -> None:
    document = copy.deepcopy(sample_plan)
    document["nodes"][0]["policy"]["retries"] = -1

    message = _invalid(document)

    assert "data.nodes[0].policy.retries: -1 is less than the minimum of 0" in message


def test_schema_falls_back_to_the_engine_accessor(
    monkeypatch: pytest.MonkeyPatch, sample_plan: dict[str, Any]
) -> None:
    fallback = plan_schema()
    fallback["title"] = "fallback schema"
    monkeypatch.setattr(schema, "_read_artifact", lambda: None)
    monkeypatch.setattr("sequence_extensions.flow.plan_schema", lambda: fallback)

    try:
        schema._schema.cache_clear()
        schema._validator.cache_clear()
        assert schema._schema()["title"] == "fallback schema"
        validate_plan(sample_plan)
    finally:
        schema._schema.cache_clear()
        schema._validator.cache_clear()
