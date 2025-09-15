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

import uuid
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from PySide6.QtWidgets import QWidget
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.tabs import Tabs

class FakeTabs:
    def __init__(self):
        self._tabs = []
    def widget(self, idx):
        try:
            return self._tabs[idx]
        except IndexError:
            return None
    def count(self):
        return len(self._tabs)
    def addTab(self, widget, icon, title):
        self._tabs.append(widget)
        return len(self._tabs) - 1
    def insertTab(self, idx, widget, title):
        self._tabs.insert(idx, widget)
        return idx
    def removeTab(self, idx):
        if int(idx) < 0 or int(idx) >= len(self._tabs):
            return
        self._tabs.pop(idx)
    def indexOf(self, widget):
        if widget not in self._tabs:
            return -1
        return self._tabs.index(widget)
    def setTabIcon(self, idx, icon):
        pass
    def setTabToolTip(self, idx, tooltip):
        pass
    def setTabText(self, idx, text):
        pass
    def currentIndex(self):
        return 0
    def tabText(self, idx):
        return "Tab Text"
    def tabToolTip(self, idx):
        return "Tab Tooltip"

class FakeColumn:
    def __init__(self):
        self._tabs = FakeTabs()
    def get_tabs(self):
        return self._tabs
    def get_column(self):
        return self

class FakeLayout:
    def __init__(self):
        self._columns = [FakeColumn(), FakeColumn()]
    def get_tabs_by_idx(self, idx):
        return self._columns[idx].get_tabs()
    def get_column_by_idx(self, idx):
        return self._columns[idx]

@pytest.fixture(autouse=True)
def set_tab_constants(monkeypatch):
    monkeypatch.setattr(Tab, "TAB_CHAT", 0)
    monkeypatch.setattr(Tab, "TAB_NOTEPAD", 1)
    monkeypatch.setattr(Tab, "TAB_FILES", 2)
    monkeypatch.setattr(Tab, "TAB_TOOL_PAINTER", 3)
    monkeypatch.setattr(Tab, "TAB_TOOL_CALENDAR", 4)
    monkeypatch.setattr(Tab, "TAB_TOOL", 5)

@pytest.fixture
def fake_window():
    window = MagicMock()
    layout = FakeLayout()
    window.ui = MagicMock()
    window.ui.layout = layout
    fake_explorer_widget = MagicMock(spec=QWidget)
    fake_painter_widget = MagicMock(spec=QWidget)
    fake_calendar_widget = MagicMock(spec=QWidget)
    window.ui.chat = MagicMock()
    window.ui.chat.output = MagicMock()
    window.ui.chat.output.explorer = MagicMock(setup=lambda: fake_explorer_widget)
    window.ui.chat.output.painter = MagicMock(setup=lambda: fake_painter_widget)
    window.ui.chat.output.calendar = MagicMock(setup=lambda: fake_calendar_widget)
    window.ui.painter = MagicMock(spec=QWidget)
    window.controller = MagicMock()
    tabs_ctrl = MagicMock()
    tabs_ctrl.get_current_column_idx.return_value = 0
    window.controller.ui = MagicMock()
    window.controller.ui.tabs = tabs_ctrl
    notepad = MagicMock()
    notepad.create.return_value = (MagicMock(spec=QWidget), 0, 1)
    window.controller.notepad = notepad
    window.controller.notepad.load = MagicMock()
    tool = MagicMock()
    tool.as_tab.return_value = MagicMock(spec=QWidget)
    tool.tab_icon = "tool-icon"
    tool.tab_title = "tool-title"
    window.tools = MagicMock()
    window.tools.get.return_value = tool
    window.core = MagicMock()
    config = MagicMock()
    config.get.return_value = None
    window.core.config = config
    window.core.ctx = MagicMock()
    window.core.ctx.output = MagicMock()
    window.core.ctx.output.mapping = {}
    window.core.ctx.output.last_pids = {}
    window.core.ctx.output.last_pid = 0
    container_widget = MagicMock(spec=QWidget)
    container_widget.setOwner = MagicMock()
    window.core.ctx.container = MagicMock()
    window.core.ctx.container.get.return_value = container_widget
    window.core.notepad = MagicMock()
    window.core.notepad.import_from_db.return_value = None
    return window

@pytest.fixture
def tabs_instance(fake_window):
    return Tabs(window=fake_window)

def test_get_tab_by_index(tabs_instance, fake_window):
    fake_owner = MagicMock()
    fake_widget = MagicMock(spec=QWidget)
    fake_widget.getOwner = MagicMock(return_value=fake_owner)
    tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    tabs._tabs.append(fake_widget)
    ret = tabs_instance.get_tab_by_index(0, 0)
    assert ret is fake_owner
    ret_none = tabs_instance.get_tab_by_index(10, 0)
    assert ret_none is None

def test_get_tab_by_pid(tabs_instance):
    fake_tab = MagicMock()
    tabs_instance.pids[10] = fake_tab
    ret = tabs_instance.get_tab_by_pid(10)
    assert ret is fake_tab
    ret_none = tabs_instance.get_tab_by_pid(999)
    assert ret_none is None

def test_get_first_tab_by_type(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab2 = MagicMock()
    fake_tab1.type = 1
    fake_tab2.type = 1
    tabs_instance.pids[0] = fake_tab1
    tabs_instance.pids[1] = fake_tab2
    ret = tabs_instance.get_first_tab_by_type(1)
    assert ret is fake_tab1
    ret_none = tabs_instance.get_first_tab_by_type(999)
    assert ret_none is None

def test_get_active_pid(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.pid = 123
    fake_widget = MagicMock(spec=QWidget)
    fake_widget.getOwner = MagicMock(return_value=fake_tab)
    tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    tabs._tabs.append(fake_widget)
    fake_window.controller.ui.tabs.get_current_column_idx.return_value = 0
    original_index = tabs.count()
    tabs._tabs.insert(0, fake_widget)
    ret = tabs_instance.get_active_pid()
    assert ret == 123

def test_add_tabs(tabs_instance, fake_window, monkeypatch):
    monkeypatch.setattr(tabs_instance, "add_chat", lambda tab: setattr(tab, "idx", 0))
    tab = tabs_instance.add(Tab.TAB_CHAT, "Chat", "icon", None, None, None)
    assert tab.pid == 0
    assert tab in tabs_instance.pids.values()
    assert isinstance(tab.uuid, uuid.UUID)

def test_append_tabs_chat(tabs_instance, fake_window, monkeypatch):
    monkeypatch.setattr(tabs_instance, "add_chat", lambda tab: setattr(tab, "idx", 0))
    initial_last_pid = tabs_instance.last_pid
    tab = tabs_instance.append(Tab.TAB_CHAT, "tool", 0, 0)
    assert tab.pid == initial_last_pid + 1
    assert tab in tabs_instance.pids.values()
    assert tab.new_idx == 1

def test_append_tabs_notepad(tabs_instance, fake_window, monkeypatch):
    called = False
    def fake_add_notepad(tab):
        setattr(tab, "idx", 0)
    monkeypatch.setattr(tabs_instance, "add_notepad", fake_add_notepad)
    fake_load = fake_window.controller.notepad.load
    initial_last_pid = tabs_instance.last_pid
    tab = tabs_instance.append(Tab.TAB_NOTEPAD, "tool", 0, 0)
    fake_load.assert_called()
    assert tab.pid == initial_last_pid + 1

def test_restore(tabs_instance, fake_window, monkeypatch):
    def fake_add_chat(tab):
        setattr(tab, "idx", 0)
    monkeypatch.setattr(tabs_instance, "add_chat", fake_add_chat)
    data = {
        "uuid": uuid.uuid4(),
        "pid": 5,
        "type": Tab.TAB_CHAT,
        "title": "Restored Chat",
        "data_id": None,
        "tooltip": "Tip",
        "custom_name": False,
        "column_idx": 0,
        "tool_id": None
    }
    tabs_instance.restore(data)
    assert 5 in tabs_instance.pids
    max_pid = max(tabs_instance.pids.keys())
    assert tabs_instance.last_pid == max_pid

def test_remove_tab_by_idx(tabs_instance, fake_window, monkeypatch):
    fake_tab = MagicMock()
    fake_tab.pid = 7
    fake_tab.idx = 0
    fake_tab.column_idx = 0
    fake_tab.cleanup = MagicMock()
    tabs_instance.pids[7] = fake_tab
    tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    fake_widget = MagicMock(spec=QWidget)
    fake_widget.getOwner = MagicMock(return_value=fake_tab)
    tabs._tabs.insert(0, fake_widget)
    monkeypatch.setattr(tabs, "currentIndex", lambda: 0)
    tabs_instance.remove_tab_by_idx(0, 0)
    assert 7 not in tabs_instance.pids

def test_remove(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.pid = 8
    fake_tab.idx = 0
    fake_tab.column_idx = 0
    fake_tab.cleanup = MagicMock()
    tabs_instance.pids[8] = fake_tab
    tabs_instance.remove(8)
    assert 8 not in tabs_instance.pids

def test_remove_all(tabs_instance, fake_window):
    fake_tab1 = MagicMock()
    fake_tab1.pid = 1
    fake_tab1.cleanup = MagicMock()
    fake_tab2 = MagicMock()
    fake_tab2.pid = 2
    fake_tab2.cleanup = MagicMock()
    tabs_instance.pids[1] = fake_tab1
    tabs_instance.pids[2] = fake_tab2
    fake_window.core.ctx.output.clear = MagicMock()
    tabs_instance.remove_all()
    assert tabs_instance.pids == {}
    fake_window.core.ctx.output.clear.assert_called()

def test_remove_all_by_type(tabs_instance, fake_window, monkeypatch):
    fake_chat = MagicMock()
    fake_chat.pid = 10
    fake_chat.type = Tab.TAB_CHAT
    fake_chat.column_idx = 0
    fake_chat.cleanup = MagicMock()
    fake_notepad = MagicMock()
    fake_notepad.pid = 11
    fake_notepad.type = Tab.TAB_NOTEPAD
    fake_notepad.column_idx = 0
    fake_notepad.cleanup = MagicMock()
    tabs_instance.pids[10] = fake_chat
    tabs_instance.pids[11] = fake_notepad
    monkeypatch.setattr(tabs_instance, "count_by_type", lambda t: 1 if t == Tab.TAB_CHAT else 1)
    tabs_instance.remove_all_by_type(Tab.TAB_NOTEPAD, 0)
    assert 11 not in tabs_instance.pids
    tabs_instance.remove_all_by_type(Tab.TAB_CHAT, 0)
    assert 10 in tabs_instance.pids

def test_get_tabs_by_type(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab1.type = 3
    fake_tab2 = MagicMock()
    fake_tab2.type = 3
    tabs_instance.pids[0] = fake_tab1
    tabs_instance.pids[1] = fake_tab2
    tabs = tabs_instance.get_tabs_by_type(3)
    assert len(tabs) == 2

def test_count_by_type(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab1.type = 2
    fake_tab2 = MagicMock()
    fake_tab2.type = 2
    tabs_instance.pids[0] = fake_tab1
    tabs_instance.pids[1] = fake_tab2
    count = tabs_instance.count_by_type(2)
    assert count == 2

def test_get_min_max_pid(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab1.type = 0
    fake_tab2 = MagicMock()
    fake_tab2.type = 0
    tabs_instance.pids[3] = fake_tab1
    tabs_instance.pids[7] = fake_tab2
    min_pid = tabs_instance.get_min_pid()
    max_pid = tabs_instance.get_max_pid()
    assert min_pid == 3
    assert max_pid == 7

def test_get_max_data_id_by_type(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab1.type = 1
    fake_tab1.data_id = 5
    fake_tab2 = MagicMock()
    fake_tab2.type = 1
    fake_tab2.data_id = 10
    tabs_instance.pids[0] = fake_tab1
    tabs_instance.pids[1] = fake_tab2
    max_data = tabs_instance.get_max_data_id_by_type(1)
    assert max_data == 10

def test_get_order_by_idx_and_type(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab1.type = 4
    fake_tab1.idx = 2
    fake_tab2 = MagicMock()
    fake_tab2.type = 4
    fake_tab2.idx = 5
    tabs_instance.pids[0] = fake_tab1
    tabs_instance.pids[1] = fake_tab2
    order = tabs_instance.get_order_by_idx_and_type(5, 4)
    assert order == 2
    order_invalid = tabs_instance.get_order_by_idx_and_type(100, 4)
    assert order_invalid == -1

def test_get_min_idx_by_type(tabs_instance):
    fake_tab1 = MagicMock()
    fake_tab1.type = 2
    fake_tab1.idx = 3
    fake_tab1.column_idx = 0
    fake_tab2 = MagicMock()
    fake_tab2.type = 2
    fake_tab2.idx = 1
    fake_tab2.column_idx = 0
    tabs_instance.pids[0] = fake_tab1
    tabs_instance.pids[1] = fake_tab2
    min_idx = tabs_instance.get_min_idx_by_type(2, 0)
    assert min_idx == 1

def test_get_min_idx_by_type_exists(tabs_instance):
    fake_tab = MagicMock()
    fake_tab.type = 2
    fake_tab.idx = 4
    fake_tab.column_idx = 0
    tabs_instance.pids[0] = fake_tab
    min_idx, col_idx, exists = tabs_instance.get_min_idx_by_type_exists(2, 0)
    assert min_idx == 4
    assert col_idx == 0
    assert exists is True

def test_get_prev_next_idx_from(tabs_instance, fake_window):
    tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    fake_tab_prev = MagicMock(spec=QWidget)
    fake_owner_prev = MagicMock()
    fake_owner_prev.column_idx = 0
    fake_tab_prev.getOwner = MagicMock(return_value=fake_owner_prev)
    fake_tab_next = MagicMock(spec=QWidget)
    fake_owner_next = MagicMock()
    fake_owner_next.column_idx = 0
    fake_tab_next.getOwner = MagicMock(return_value=fake_owner_next)
    tabs._tabs.extend([fake_tab_prev, fake_tab_next])
    prev_idx, prev_exists = tabs_instance.get_prev_idx_from(1, 0)
    assert prev_idx == 0 and prev_exists is True
    next_idx, next_exists = tabs_instance.get_next_idx_from(0, 0)
    assert next_idx == 1 and next_exists is True
    prev_bad, exists_bad = tabs_instance.get_prev_idx_from(0, 0)
    assert prev_bad == -1 and exists_bad is False

def test_get_max_idx_by_column(tabs_instance, fake_window):
    tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    fake_widget1 = MagicMock(spec=QWidget)
    fake_owner1 = MagicMock()
    fake_owner1.column_idx = 0
    fake_owner1.idx = 2
    fake_widget1.getOwner = MagicMock(return_value=fake_owner1)
    fake_widget2 = MagicMock(spec=QWidget)
    fake_owner2 = MagicMock()
    fake_owner2.column_idx = 0
    fake_owner2.idx = 5
    fake_widget2.getOwner = MagicMock(return_value=fake_owner2)
    tabs._tabs.extend([fake_widget1, fake_widget2])
    max_idx = tabs_instance.get_max_idx_by_column(0)
    assert max_idx == 5

def test_update(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.column_idx = 0
    fake_tab.idx = 0
    fake_tab.child = MagicMock(spec=QWidget)
    tabs_instance.pids[0] = fake_tab
    tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    tabs._tabs.append(fake_tab.child)
    fake_window.ui.layout.get_tabs_by_idx(0).indexOf = lambda child: 0
    fake_window.ui.layout.get_tabs_by_idx(0).tabText = lambda idx: "Updated"
    fake_window.ui.layout.get_tabs_by_idx(0).tabToolTip = lambda idx: "Tooltip"
    tabs_instance.update_column(0)
    assert fake_tab.idx == 0
    assert fake_tab.title == "Updated"
    assert fake_tab.tooltip == "Tooltip"
    assert isinstance(fake_tab.updated_at, datetime)

def test_update_title(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.pid = 20
    fake_tab.idx = 0
    fake_tab.column_idx = 0
    tabs_instance.pids[20] = fake_tab
    fake_tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    fake_tabs.setTabText = MagicMock()
    fake_tabs.setTabToolTip = MagicMock()
    monkey_tab = fake_tab
    monkey_tab.custom_name = False
    tabs_instance.get_tab_by_index = MagicMock(return_value=monkey_tab)
    tabs_instance.update_title(0, "New Title", "New Tooltip")
    fake_tabs.setTabText.assert_called_with(0, "New Title")
    fake_tabs.setTabToolTip.assert_called_with(0, "New Tooltip")
    assert fake_tab.custom_name is True

def test_toggle_debug(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.pid = 30
    fake_tab.idx = 0
    fake_tab.column_idx = 0
    fake_tab.title = "Title"
    fake_tab.tooltip = "Tip"
    tabs_instance.pids[30] = fake_tab
    fake_tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    fake_tabs._tabs.append(MagicMock(spec=QWidget, getOwner=lambda: fake_tab))
    fake_tabs.setTabText = MagicMock()
    fake_tabs.setTabToolTip = MagicMock()
    fake_window.core.config.save = MagicMock()
    tabs_instance.toggle_debug(True)
    fake_tabs.setTabText.assert_called()
    tabs_instance.toggle_debug(False)
    fake_window.core.config.save.assert_called()

def test_from_widget(tabs_instance, fake_window):
    pass

def test_save(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.pid = 40
    fake_tab.idx = 0
    fake_tab.title = "SaveTitle"
    fake_tab.tooltip = "SaveTip"
    fake_tab.data_id = None
    fake_tab.custom_name = False
    fake_tab.column_idx = 0
    fake_tab.tool_id = None
    tabs_instance.pids[40] = fake_tab
    fake_tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    fake_tabs.currentIndex = lambda: 0
    fake_window.core.config.set = MagicMock()
    fake_window.core.config.save = MagicMock()
    tabs_instance.save()
    fake_window.core.config.set.assert_called()
    fake_window.core.config.save.assert_called()

def test_move_tab(tabs_instance, fake_window):
    fake_tab = MagicMock()
    fake_tab.idx = 0
    fake_tab.column_idx = 0
    fake_tab.child = MagicMock(spec=QWidget)
    fake_tab.icon = MagicMock(return_value="icon")
    tabs_instance.pids[50] = fake_tab
    old_tabs = fake_window.ui.layout.get_tabs_by_idx(0)
    old_tabs._tabs.append(fake_tab.child)
    new_column = fake_window.ui.layout.get_tabs_by_idx(1)
    original_count = new_column.count()
    tabs_instance.move_tab(fake_tab, 1)
    assert fake_tab.column_idx == 1
    assert new_column.count() == original_count + 1
    assert fake_tab.child in new_column._tabs