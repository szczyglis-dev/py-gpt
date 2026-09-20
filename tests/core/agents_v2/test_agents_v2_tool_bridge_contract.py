#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pygpt_net.core.agents_v2 import tool_bridge


def test_agents_v2_tool_bridge_register_get_pop_roundtrip():
    ctx = object()
    request = {"ctx": ctx, "result": None}

    tool_bridge.register(ctx, request)
    try:
        assert tool_bridge.get(ctx) is request
        assert tool_bridge.pop(ctx) is request
        assert tool_bridge.get(ctx) is None
    finally:
        tool_bridge.discard(ctx)


def test_agents_v2_tool_bridge_rejects_invalid_registration():
    ctx = object()

    tool_bridge.register(None, {"ctx": None})
    tool_bridge.register(ctx, "not-a-dict")

    assert tool_bridge.get(None) is None
    assert tool_bridge.get(ctx) is None


def test_agents_v2_tool_bridge_identity_guard_prevents_wrong_context_access():
    ctx = object()
    wrong_ctx = object()
    request = {"ctx": wrong_ctx}

    tool_bridge.register(ctx, request)
    try:
        assert tool_bridge.get(ctx) is None
        assert tool_bridge.pop(ctx) is None
    finally:
        tool_bridge.discard(ctx, request)


def test_agents_v2_tool_bridge_pending_state_and_conditional_discard():
    ctx = object()
    first = {"ctx": ctx}
    second = {"ctx": ctx}

    tool_bridge.register(ctx, first)
    tool_bridge.mark_pending(ctx, True)
    assert tool_bridge.is_pending(ctx) is True

    tool_bridge.register(ctx, second)
    tool_bridge.discard(ctx, first)
    assert tool_bridge.get(ctx) is second

    tool_bridge.mark_pending(ctx, False)
    assert tool_bridge.is_pending(ctx) is False

    tool_bridge.discard(ctx, second)
    assert tool_bridge.get(ctx) is None
