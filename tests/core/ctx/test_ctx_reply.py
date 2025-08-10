#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

from typing import Dict, Any
from unittest.mock import Mock

from pygpt_net.core.ctx.reply import Reply, ReplyContext

def test_replycontext_defaults_and_to_dict_none_fields():
    rc = ReplyContext()
    assert rc.type is None
    assert rc.bridge_context is None
    assert rc.ctx is None
    assert rc.prev_ctx is None
    assert rc.parent_id is None
    assert rc.input == ""
    assert rc.internal is False
    assert rc.cmds == []
    d = rc.to_dict()
    assert d == {
        "type": None,
        "bridge_context": None,
        "ctx": None,
        "prev_ctx": None,
        "parent_id": None,
        "input": "",
        "cmds": [],
    }

def test_to_dict_with_nested_objects_calls_to_dict_and_returns_nested_dicts():
    rc = ReplyContext()
    rc.type = ReplyContext.CMD_EXECUTE
    bridge = Mock()
    bridge.to_dict.return_value = {"bridge": True}
    ctx = Mock()
    ctx.to_dict.return_value = {"ctx": 123}
    prev_ctx = Mock()
    prev_ctx.to_dict.return_value = {"prev": "x"}
    rc.bridge_context = bridge
    rc.ctx = ctx
    rc.prev_ctx = prev_ctx
    rc.parent_id = "parent-1"
    rc.input = "command"
    rc.cmds = ["a", "b"]
    result = rc.to_dict()
    bridge.to_dict.assert_called_once()
    ctx.to_dict.assert_called_once()
    prev_ctx.to_dict.assert_called_once()
    assert result["type"] == ReplyContext.CMD_EXECUTE
    assert result["bridge_context"] == {"bridge": True}
    assert result["ctx"] == {"ctx": 123}
    assert result["prev_ctx"] == {"prev": "x"}
    assert result["parent_id"] == "parent-1"
    assert result["input"] == "command"
    assert result["cmds"] == ["a", "b"]
    assert result["cmds"] is rc.cmds

def test_reply_init_assigns_window():
    r = Reply()
    assert r.window is None
    mock_window = Mock()
    r2 = Reply(window=mock_window)
    assert r2.window is mock_window

def test_to_dict_does_not_include_internal_key():
    rc = ReplyContext()
    rc.internal = True
    d = rc.to_dict()
    assert "internal" not in d