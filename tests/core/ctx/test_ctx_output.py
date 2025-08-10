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

import pytest
from unittest.mock import Mock

from pygpt_net.core.ctx.output import Output

try:
    from pygpt_net.core.tabs.tab import Tab as RealTab
    TAB_CHAT = RealTab.TAB_CHAT
except Exception:
    TAB_CHAT = "chat"


class Meta:
    def __init__(self, id):
        self.id = id


class FakeTab:
    def __init__(self, pid, column_idx=0, type_=TAB_CHAT, data_id=None):
        self.pid = pid
        self.column_idx = column_idx
        self.type = type_
        self.data_id = data_id


class FakeTabs:
    def __init__(self, num_cols):
        self.NUM_COLS = num_cols
        self._tabs = {}
        self._active_pid = None

    def add_tab(self, tab):
        self._tabs[tab.pid] = tab

    def set_active(self, pid):
        self._active_pid = pid

    def get_active_pid(self):
        return self._active_pid

    def get_tab_by_pid(self, pid):
        return self._tabs.get(pid)


@pytest.fixture
def window():
    win = Mock()
    ui = Mock()
    ui.nodes = {"output": {}, "output_plain": {}}
    win.ui = ui
    win.core = Mock()
    win.core.tabs = FakeTabs(num_cols=3)
    return win


def test_init_creates_mappings(window):
    out = Output(window)
    out.init()
    assert out.initialized is True
    assert set(out.mapping.keys()) == {0, 1, 2}
    assert set(out.last_pids.keys()) == {0, 1, 2}
    for v in out.mapping.values():
        assert isinstance(v, dict)
    for v in out.last_pids.values():
        assert isinstance(v, dict)


def test_init_preserves_without_force_and_resets_with_force(window):
    out = Output(window)
    out.init()
    out.mapping[0][123] = "keep"
    out.init()
    assert out.mapping[0][123] == "keep"
    out.init(force=True)
    assert out.mapping[0] == {}


def test_store_returns_zero_if_no_tab_or_wrong_type(window):
    out = Output(window)
    window.core.tabs.set_active(1)
    meta = Meta(5)
    assert out.store(meta) == 0
    tab = FakeTab(pid=2, column_idx=0, type_="not_chat")
    window.core.tabs.add_tab(tab)
    window.core.tabs.set_active(2)
    assert out.store(meta) == 0


def test_store_maps_meta_and_sets_tab_data_id(window):
    out = Output(window)
    tab = FakeTab(pid=7, column_idx=1, type_=TAB_CHAT)
    window.core.tabs.add_tab(tab)
    window.core.tabs.set_active(7)
    meta = Meta(99)
    pid = out.store(meta)
    assert pid == 7
    assert out.mapping[1][7] == 99
    assert out.last_pids[1][99] == 7
    assert out.last_pid == 7
    assert window.core.tabs.get_tab_by_pid(7).data_id == 99


def test_is_mapped_true_and_false(window):
    out = Output(window)
    out.init()
    meta = Meta(42)
    out.mapping[0][1] = 42
    assert out.is_mapped(meta) is True
    assert out.is_mapped(Meta(43)) is False


def test_get_meta_returns_meta_id_or_none(window):
    out = Output(window)
    out.init()
    out.mapping[0][1] = 55
    assert out.get_meta(1) == 55
    assert out.get_meta(999) is None


def test_prepare_meta_returns_existing_and_stores_data_id(window):
    out = Output(window)
    out.init()
    t1 = FakeTab(pid=2, column_idx=0, type_=TAB_CHAT)
    out.mapping[0][2] = 111
    assert out.prepare_meta(t1) == 111
    t2 = FakeTab(pid=3, column_idx=2, type_=TAB_CHAT, data_id=222)
    assert out.prepare_meta(t2) == 222
    assert out.mapping[2][3] == 222
    assert out.last_pids[2][222] == 3
    assert out.last_pid == 3
    t3 = FakeTab(pid=4, column_idx=1, type_=TAB_CHAT, data_id=None)
    assert out.prepare_meta(t3) is None


def test_get_mapped_behaviour(window):
    out = Output(window)
    out.init()
    window.core.tabs.set_active(123)
    assert out.get_mapped(Meta(1)) is None
    tab_active = FakeTab(pid=10, column_idx=0, type_=TAB_CHAT)
    window.core.tabs.add_tab(tab_active)
    window.core.tabs.set_active(10)
    out.mapping[0][10] = 5
    out.mapping[0][11] = 5
    assert out.get_mapped(Meta(5)) == 10
    window.core.tabs.set_active(100)
    out.mapping[0].clear()
    out.mapping[0][1] = 7
    out.mapping[0][2] = 7
    window.core.tabs.add_tab(FakeTab(pid=100, column_idx=0, type_=TAB_CHAT))
    window.core.tabs.set_active(100)
    assert out.get_mapped(Meta(7)) == 2


def test_is_empty_checks_active_pid(window):
    out = Output(window)
    out.init()
    window.core.tabs.set_active(5)
    assert out.is_empty() is True
    out.mapping[0][5] = 77
    assert out.is_empty() is False


def test_get_pid_none_and_mapped_and_store_behaviour(window):
    out = Output(window)
    out.init()
    assert out.get_pid(None) is None
    tab = FakeTab(pid=1, column_idx=0, type_=TAB_CHAT)
    window.core.tabs.add_tab(tab)
    window.core.tabs.set_active(1)
    out.mapping[0][1] = 99
    assert out.get_pid(Meta(99)) == 1
    tab2 = FakeTab(pid=8, column_idx=2, type_=TAB_CHAT)
    window.core.tabs.add_tab(tab2)
    window.core.tabs.set_active(8)
    assert out.get_pid(Meta(1234)) == 8
    assert out.mapping[2][8] == 1234


def test_clear_resets_state(window):
    out = Output(window)
    out.mapping = {0: {1: 2}}
    out.last_pids = {0: {2: 1}}
    out.last_pid = 5
    out.initialized = True
    out.clear()
    assert out.mapping == {}
    assert out.last_pids == {}
    assert out.last_pid == 0
    assert out.initialized is False


def test_get_current_and_plain_use_get_pid_and_nodes(window):
    out = Output(window)
    node1 = object()
    node2 = object()
    window.ui.nodes["output"] = {5: node1, 7: node2}
    out.get_pid = Mock(return_value=7)
    assert out.get_current(Meta(0)) is node2
    out.get_pid = Mock(return_value=999)
    assert out.get_current(Meta(0)) is node1
    window.ui.nodes["output_plain"] = {2: "plain1", 3: "plain2"}
    out.get_pid = Mock(return_value=3)
    assert out.get_current_plain(Meta(0)) == "plain2"
    out.get_pid = Mock(return_value=999)
    assert out.get_current_plain(Meta(0)) == "plain1"


def test_get_by_pid_and_plain_return_specific_or_first(window):
    out = Output(window)
    node1 = object()
    node2 = object()
    window.ui.nodes["output"] = {3: node1, 4: node2}
    assert out.get_by_pid(4) is node2
    assert out.get_by_pid(999) is node1
    window.ui.nodes["output_plain"] = {8: "p1", 9: "p2"}
    assert out.get_by_pid_plain(9) == "p2"
    assert out.get_by_pid_plain(999) == "p1"


def test_get_all_and_get_all_plain(window):
    out = Output(window)
    a = object()
    b = object()
    window.ui.nodes["output"] = {1: a, 2: b}
    assert out.get_all() == [a, b]
    window.ui.nodes["output_plain"] = {10: "p1", 11: "p2"}
    assert out.get_all_plain() == ["p1", "p2"]


def test_remove_pid_behaviour(window):
    out = Output(window)
    tab = FakeTab(pid=20, column_idx=1, type_=TAB_CHAT)
    window.core.tabs.add_tab(tab)
    window.core.tabs.set_active(20)
    meta = Meta(200)
    out.store(meta)
    assert 20 in out.mapping[1]
    out.remove_pid(20)
    assert 20 not in out.mapping[1]
    assert out.last_pid == 0
    out.init()
    out.last_pids[30] = "to_delete"
    out.last_pid = 30
    out.remove_pid(30)
    assert 30 not in out.last_pids
    assert out.last_pid == 0