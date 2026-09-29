#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents_v2.verbose import AgentsV2VerboseLogger


def make_logger(verbose=False, workflow=False):
    window = MagicMock()
    values = {
        "agent.v2.verbose": verbose,
        "agent.v2.log_workflow": workflow,
    }
    window.core.config.get.side_effect = lambda key, default=False: values.get(key, default)
    return AgentsV2VerboseLogger(window, "run-test")


def test_agents_v2_verbose_safe_value_redacts_nested_credentials():
    value = {
        "api_key": "secret-1",
        "nested": {"authorization": "Bearer secret", "safe": 7},
    }

    safe = AgentsV2VerboseLogger._safe_value(value)

    assert safe["api_key"] == "<redacted>"
    assert safe["nested"]["authorization"] == "<redacted>"
    assert safe["nested"]["safe"] == 7


def test_agents_v2_verbose_safe_value_serializes_dataclasses_and_sequences():
    @dataclass
    class Item:
        value: int

    safe = AgentsV2VerboseLogger._safe_value({"items": [Item(3)]})

    assert safe == {"items": [{"value": 3}]}


def test_agents_v2_verbose_compact_workflow_skips_orchestration_tool_calls(capsys):
    logger = make_logger(verbose=False, workflow=True)

    logger.log("TOOL CALL", {"tool_name": "agent_create", "tool_kwargs": {"name": "x"}})
    logger.log("TOOL CALL", {"tool_name": "read_file", "tool_kwargs": {"path": "/tmp/a"}})

    output = capsys.readouterr().out
    assert "agent_create" not in output
    assert "tool call: read_file" in output


def test_agents_v2_verbose_full_mode_prints_header_and_redacted_payload(capsys):
    logger = make_logger(verbose=True, workflow=False)

    logger.log("TEST", {"password": "secret", "value": 1}, actor="w01")

    output = capsys.readouterr().out
    assert "[Agents v2]" in output
    assert "[run=run-test]" in output
    assert "[w01][TEST]" in output
    assert "<redacted>" in output
    assert "secret" not in output
