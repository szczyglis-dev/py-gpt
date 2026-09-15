#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pygpt_net.core.agents.custom.router import build_router_instruction, parse_route_output


def test_router_instruction_contains_allowed_ids_friendly_names_and_optional_roles():
    text = build_router_instruction(
        "Router",
        "router-1",
        ["coder", "research"],
        {
            "coder": {"name": "Coder", "role": "writes code"},
            "research": "Researcher",
        },
    )

    assert "router-1" in text
    assert "allowed_routes: [coder, research]" in text
    assert '"coder": "Coder"' in text
    assert '"research": "Researcher"' in text
    assert '"coder": "writes code"' in text


def test_router_instruction_omits_roles_line_when_no_roles_are_defined():
    text = build_router_instruction("Router", "id", ["a"], {"a": "Agent A"})

    assert "route roles" not in text


def test_parse_route_output_accepts_allowed_route_and_end():
    routed = parse_route_output('{"route":"coder","content":"go"}', ["coder"])
    ended = parse_route_output('{"route":"END","content":"done"}', ["coder"])

    assert routed.valid is True
    assert routed.route == "coder"
    assert routed.content == "go"
    assert ended.valid is True
    assert ended.route == "end"


def test_parse_route_output_extracts_fenced_or_embedded_json():
    fenced = parse_route_output('```json\n{"route":"end","content":"ok"}\n```', [])
    embedded = parse_route_output('prefix {"route":"a","content":"ok"} suffix', ["a"])

    assert fenced.valid is True and fenced.route == "end"
    assert embedded.valid is True and embedded.route == "a"


def test_parse_route_output_rejects_disallowed_route_and_malformed_json():
    disallowed = parse_route_output('{"route":"other","content":"x"}', ["allowed"])
    malformed = parse_route_output("not json", ["allowed"])

    assert disallowed.valid is False
    assert disallowed.route is None
    assert "Invalid or disallowed route" in disallowed.error
    assert malformed.valid is False
    assert malformed.content == "not json"
    assert malformed.error == "Malformed JSON"


def test_extract_json_block_supports_fenced_embedded_and_missing_json():
    from pygpt_net.core.agents.custom.router import _extract_json_block

    assert _extract_json_block('```json\n{"a":1}\n```') == '{"a":1}'
    assert _extract_json_block('prefix {"a":1} suffix') == '{"a":1}'
    assert _extract_json_block('no object') is None
