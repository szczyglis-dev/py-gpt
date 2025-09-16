#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.09 00:00:00                  #
# ================================================== #

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from pygpt_net.core.tabs.tab import Tab

def test_default_initialization():
    t = Tab()
    assert t.uuid is None
    assert t.pid is None
    assert t.idx == 0
    assert t.type == Tab.TAB_CHAT
    assert t.title == ""
    assert t.icon is None
    assert t.tooltip is None
    assert t.data_id is None
    assert t.new_idx is None
    assert t.custom_name is False
    assert t.child is None
    assert t.parent is None
    assert t.column_idx == 0
    assert t.tool_id is None
    assert t.loaded is False
    assert t.refs == []
    assert isinstance(t.created_at, datetime)
    assert isinstance(t.updated_at, datetime)
    assert t.created_at == t.updated_at

def test_to_dict():
    child = MagicMock()
    parent = MagicMock()
    t = Tab(uuid="123", pid=42, idx=1, type=Tab.TAB_FILES, title="Test", icon="icon.png", tooltip="Tip", data_id="data", new_idx=5, custom_name=True, child=child, parent=parent, column_idx=2, tool_id="tool")
    d = t.to_dict()
    assert d["uuid"] == "123"
    assert d["pid"] == 42
    assert d["idx"] == 1
    assert d["type"] == Tab.TAB_FILES
    assert d["title"] == "Test"
    assert d["loaded"] is False
    assert d["icon"] == "icon.png"
    assert d["tooltip"] == "Tip"
    assert d["data_id"] == "data"
    assert d["parent"] == str(parent)
    assert d["custom_name"] is True
    assert d["custom_idx"] == 5
    assert "created_at" in d
    assert "updated_at" in d
    assert d["column_idx"] == 2
    assert d["tool_id"] == "tool"
    assert d["refs"] == []

def test_str_representation():
    t = Tab(uuid="abc", title="StrTest")
    s1 = str(t)
    s2 = str(t.to_dict())
    assert s1 == s2

def test_add_ref():
    t = Tab()
    ref = MagicMock()
    t.add_ref(ref)
    assert len(t.refs) == 1
    t.add_ref(ref)
    assert len(t.refs) == 1
    ref2 = MagicMock()
    t.add_ref(ref2)
    assert len(t.refs) == 2

def test_delete_refs():
    child = MagicMock()
    child.cleanup = MagicMock()
    ref_with_delete = MagicMock()
    ref_with_delete.deleteLater = MagicMock()
    ref_without_delete = object()
    t = Tab(child=child)
    t.add_ref(ref_with_delete)
    t.add_ref(ref_without_delete)
    t.delete_refs()
    child.cleanup.assert_called_once()
    ref_with_delete.deleteLater.assert_called_once()
    assert t.refs == []

def test_cleanup_normal():
    on_delete = MagicMock()
    child = MagicMock()
    child.cleanup = MagicMock()
    ref = MagicMock()
    ref.deleteLater = MagicMock()
    t = Tab(on_delete=on_delete, child=child)
    t.add_ref(ref)
    t.cleanup()
    on_delete.assert_called_once_with(t)
    child.cleanup.assert_called_once()
    ref.deleteLater.assert_called_once()
    assert t.refs == []

def test_cleanup_exception():
    on_delete = MagicMock(side_effect=Exception("fail"))
    child = MagicMock()
    child.cleanup = MagicMock()
    ref = MagicMock()
    ref.deleteLater = MagicMock()
    t = Tab(on_delete=on_delete, child=child)
    t.add_ref(ref)
    t.cleanup()
    on_delete.assert_called_once_with(t)
    child.cleanup.assert_not_called()
    ref.deleteLater.assert_not_called()
    assert len(t.refs) == 1