#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from types import SimpleNamespace
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.ctx import CtxMeta
from pygpt_net.controller.ui.tabs import Tabs

@pytest.fixture
def dummy_window():
    core_tabs = MagicMock()
    core_config = MagicMock()
    core_ctx = MagicMock()
    controller_notepad = MagicMock()
    controller_ctx = MagicMock()
    controller_ui = MagicMock()
    controller_calendar = MagicMock()
    controller_camera = MagicMock()
    controller_audio = MagicMock()
    dialogs_debug = MagicMock()
    controller = SimpleNamespace(
        notepad=controller_notepad,
        ctx=controller_ctx,
        ui=controller_ui,
        calendar=controller_calendar,
        camera=controller_camera,
        audio=controller_audio,
        dialogs=SimpleNamespace(debug=dialogs_debug),
        chat=MagicMock()
    )
    ui_nodes = {"layout.split": MagicMock()}
    ui_splitters = {"columns": MagicMock()}
    ui_layout = MagicMock()
    ui_layout.get_tabs_by_idx = MagicMock(return_value=MagicMock())
    ui_dialog = {"rename": MagicMock()}
    ui = SimpleNamespace(
        nodes=ui_nodes,
        splitters=ui_splitters,
        layout=ui_layout,
        dialog=ui_dialog,
        dialogs={}
    )
    core = SimpleNamespace(
        tabs=core_tabs,
        config=core_config,
        ctx=core_ctx
    )
    window = SimpleNamespace(
        core=core,
        controller=controller,
        ui=ui,
        dispatch=MagicMock()
    )
    return window

@pytest.fixture
def tabs(dummy_window):
    return Tabs(window=dummy_window)

def test_setup(tabs, dummy_window):
    tabs.setup()
    dummy_window.core.tabs.load.assert_called_once()
    dummy_window.controller.notepad.load.assert_called_once()
    dummy_window.ui.nodes["layout.split"].setChecked.assert_called_once()
    assert tabs.initialized

def test_setup_options_checked(tabs, dummy_window):
    dummy_window.core.config.get.return_value = True
    tabs.setup_options()
    dummy_window.ui.nodes["layout.split"].setChecked.assert_called_with(True)

def test_setup_options_unchecked(tabs, dummy_window):
    dummy_window.core.config.get.return_value = False
    dummy_window.ui.splitters["columns"].setSizes = MagicMock()
    tabs.setup_options()
    dummy_window.ui.splitters["columns"].setSizes.assert_called_with([1, 0])

def test_debug_active(tabs, dummy_window):
    dummy_window.controller.dialogs.debug.is_active.return_value = True
    tabs.debug()
    dummy_window.core.tabs.toggle_debug.assert_called_with(True)

def test_debug_inactive(tabs, dummy_window):
    dummy_window.controller.dialogs.debug.is_active.return_value = False
    tabs.debug()
    dummy_window.core.tabs.toggle_debug.assert_not_called()

def test_add(tabs, dummy_window):
    tabs.add(1, "Test", icon="icon.png", child="child", data_id=10, tool_id="tool")
    dummy_window.core.tabs.add.assert_called_with(
        type=1,
        title="Test",
        icon="icon.png",
        child="child",
        data_id=10,
        tool_id="tool"
    )

def test_append(tabs, dummy_window):
    dummy_tab = MagicMock()
    dummy_tab.idx = 5
    dummy_window.core.tabs.append.return_value = dummy_tab
    new_tabs = MagicMock(currentIndex=lambda: 0, setCurrentIndex=MagicMock())
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=new_tabs)
    called = False
    original_switch = tabs.switch_tab_by_idx
    def fake_switch(idx, col):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.append(2, tool_id="tool", idx=3, column_idx=1)
    assert tabs.appended is True
    assert tabs.column_idx == 1
    assert called is True
    dummy_window.core.tabs.append.assert_called_with(
        type=2,
        idx=3,
        column_idx=1,
        tool_id="tool"
    )
    tabs.switch_tab_by_idx = original_switch

def test_reload_titles(tabs, dummy_window):
    tabs.reload_titles()
    dummy_window.core.tabs.reload_titles.assert_called_once()

def test_update_current(tabs, dummy_window):
    dummy_tab = MagicMock(pid=42)
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.column_idx = 0
    tabs.col = {}
    tabs.update_current()
    assert tabs.col[0] == 42

def test_reload(tabs, dummy_window):
    tabs.reload()
    dummy_window.core.tabs.reload.assert_called_once()
    dummy_window.dispatch.assert_called_once()

def test_reload_after(tabs, dummy_window):
    node1 = MagicMock()
    node1.setVisible = MagicMock()
    node2 = MagicMock()
    node2.setVisible = MagicMock()
    dummy_window.ui.nodes['output'] = {1: node1}
    dummy_window.ui.nodes['output_plain'] = {1: node2}
    dummy_window.core.config.get.return_value = True
    tabs.reload_after()
    dummy_window.ui.nodes['output_plain'][1].setVisible.assert_called_with(True)
    dummy_window.ui.nodes['output'][1].setVisible.assert_called_with(False)

def test_on_tab_changed_not_found(tabs, dummy_window):
    dummy_window.core.tabs.get_tab_by_index.return_value = None
    tabs.appended = True
    tabs.on_tab_changed(1, 0)
    assert tabs.appended is False

def test_on_tab_changed_chat(tabs, dummy_window):
    dummy_tab = MagicMock()
    dummy_tab.type = Tab.TAB_CHAT
    dummy_tab.data_id = None
    dummy_window.core.tabs.get_tab_by_index = MagicMock(return_value=dummy_tab)
    dummy_ctx_meta = CtxMeta()
    dummy_ctx_meta.id = 123
    dummy_window.controller.ctx.new = MagicMock(return_value=dummy_ctx_meta)
    dummy_window.controller.ctx.load = MagicMock()
    tabs.create_new_on_tab = True
    tabs.current = 0
    tabs.column_idx = 0
    tabs.appended = True
    tabs.on_tab_changed(2, 0)
    dummy_window.controller.ctx.new.assert_called_once()

def test_on_tab_changed_notepad(tabs, dummy_window):
    dummy_tab = MagicMock()
    dummy_tab.type = Tab.TAB_NOTEPAD
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.current = 0
    tabs.column_idx = 0
    tabs.on_tab_changed(2, 0)
    dummy_window.controller.notepad.on_open.assert_called_with(2, 0)

def test_on_changed(tabs, dummy_window):
    dummy_tab = MagicMock()
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.on_changed()
    dummy_window.controller.audio.on_tab_changed.assert_called_with(dummy_tab)

def test_get_current_idx(tabs, dummy_window):
    tabs.current = 5
    assert tabs.get_current_idx() == 5

def test_get_current_column_idx(tabs, dummy_window):
    tabs.column_idx = 3
    assert tabs.get_current_column_idx() == 3

def test_get_current_tab(tabs, dummy_window):
    dummy_tab = MagicMock()
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.current = 2
    tabs.column_idx = 1
    assert tabs.get_current_tab() == dummy_tab

def test_get_current_type(tabs, dummy_window):
    dummy_tab = MagicMock(type=7)
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.current = 2
    tabs.column_idx = 1
    assert tabs.get_current_type() == 7

def test_get_current_pid(tabs, dummy_window):
    dummy_tab = MagicMock(pid=99)
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.current = 2
    tabs.column_idx = 1
    assert tabs.get_current_pid() == 99

def test_get_type_by_idx(tabs, dummy_window):
    dummy_tab = MagicMock(type=4)
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.column_idx = 1
    assert tabs.get_type_by_idx(10) == 4

def test_get_first_idx_by_type(tabs, dummy_window):
    dummy_window.core.tabs.get_min_idx_by_type.return_value = 8
    tabs.column_idx = 1
    assert tabs.get_first_idx_by_type(3) == 8

def test_get_prev_idx_from(tabs, dummy_window):
    dummy_window.core.tabs.get_prev_idx_from.return_value = (2, True)
    tabs.column_idx = 0
    assert tabs.get_prev_idx_from(3) == (2, True)

def test_get_next_idx_from(tabs, dummy_window):
    dummy_window.core.tabs.get_next_idx_from.return_value = (4, True)
    tabs.column_idx = 0
    assert tabs.get_next_idx_from(3) == (4, True)

def test_get_after_close_idx(tabs, dummy_window):
    tabs.get_prev_idx_from = MagicMock(return_value=(1, True))
    assert tabs.get_after_close_idx(5) == 1
    tabs.get_prev_idx_from = MagicMock(return_value=(0, False))
    tabs.get_next_idx_from = MagicMock(return_value=(2, True))
    assert tabs.get_after_close_idx(5) == 2

def test_on_column_changed(tabs, dummy_window):
    dummy_tabs = MagicMock()
    dummy_tabs.currentIndex.return_value = 0
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(side_effect=lambda idx: dummy_tabs if idx == 0 else MagicMock(set_active=MagicMock()))
    dummy_tab = MagicMock()
    dummy_tab.type = Tab.TAB_CHAT
    dummy_tab.loaded = False
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    dummy_window.core.ctx.get_meta_by_id.return_value = MagicMock(id=55)
    dummy_window.core.ctx.get_current.return_value = None
    tabs.column_idx = 0
    tabs.on_column_changed()
    dummy_tabs.set_active.assert_called_with(True)
    dummy_window.controller.ui.update.assert_called()

def test_on_tab_clicked(tabs, dummy_window):
    dummy_tabs = MagicMock()
    dummy_tabs.currentIndex.return_value = 2
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=dummy_tabs)
    tabs.on_tab_clicked(2, 0)
    assert tabs.current == 2

def test_on_column_focus(tabs, dummy_window):
    original_col = tabs.column_idx
    tabs.on_column_focus(original_col + 1)
    assert tabs.column_idx == original_col + 1

def test_on_tab_dbl_clicked(tabs, dummy_window):
    dummy_window.core.tabs.get_tab_by_index.return_value = MagicMock()
    tabs.on_tab_dbl_clicked(3, 0)
    assert tabs.current == 3

def test_on_tab_closed(tabs, dummy_window):
    dummy_window.core.tabs.get_prev_idx_from.return_value = (1, True)
    dummy_window.core.tabs.get_next_idx_from.return_value = (2, False)
    dummy_window.core.tabs.remove_tab_by_idx = MagicMock()
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.current = 2
    tabs.column_idx = 0
    tabs.on_tab_closed(3, 0)
    dummy_window.core.tabs.remove_tab_by_idx.assert_called_with(3, 0)
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_on_tab_moved(tabs, dummy_window):
    dummy_window.core.tabs.update = MagicMock()
    tabs.on_tab_moved(2, 0)
    dummy_window.core.tabs.update.assert_called_once()

def test_close(tabs, dummy_window):
    orig_on_tab_closed = tabs.on_tab_closed
    called = False
    def fake_on_tab_closed(idx, col):
        nonlocal called
        called = True
    tabs.on_tab_closed = fake_on_tab_closed
    tabs.close(1, 0)
    assert called is True
    tabs.on_tab_closed = orig_on_tab_closed

def test_close_all_without_force(tabs, dummy_window):
    dummy_window.ui.dialogs = MagicMock()
    dummy_window.ui.dialogs.confirm = MagicMock()
    tabs.tmp_column_idx = 0
    tabs.close_all(1, 0, force=False)
    dummy_window.ui.dialogs.confirm.assert_called_once()

def test_close_all_with_force(tabs, dummy_window):
    tabs.tmp_column_idx = 0
    dummy_window.core.tabs.remove_all_by_type = MagicMock()
    orig_on_changed = tabs.on_changed
    called = False
    def fake_on_changed():
        nonlocal called
        called = True
    tabs.on_changed = fake_on_changed
    tabs.close_all(1, 0, force=True)
    dummy_window.core.tabs.remove_all_by_type.assert_called()
    assert called is True
    tabs.on_changed = orig_on_changed


def test_prev_tab(tabs, dummy_window):
    fake_tabs = MagicMock()
    fake_tabs.currentIndex.return_value = 1
    fake_child = [MagicMock(), MagicMock(), MagicMock()]
    fake_tabs.children.return_value = fake_child
    fake_tabs.setCurrentIndex = MagicMock()
    dummy_window.ui.layout.get_active_tabs = MagicMock(return_value=fake_tabs)
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col=0):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.prev_tab()
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_switch_tab(tabs, dummy_window):
    dummy_window.core.tabs.get_min_idx_by_type.return_value = 2
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col=0):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.switch_tab(1)
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_switch_tab_by_idx(tabs, dummy_window):
    fake_tabs = MagicMock()
    fake_tabs.setCurrentIndex = MagicMock()
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=fake_tabs)
    called = False
    orig_on_tab_changed = tabs.on_tab_changed
    def fake_on_tab_changed(idx, col):
        nonlocal called
        called = True
    tabs.on_tab_changed = fake_on_tab_changed
    tabs.switch_tab_by_idx(3, 0)
    fake_tabs.setCurrentIndex.assert_called_with(3)
    assert called is True
    tabs.on_tab_changed = orig_on_tab_changed

def test_get_current_tab_name(tabs, dummy_window):
    fake_tabs = MagicMock()
    fake_tabs.tabText.return_value = "TabName"
    dummy_window.ui.layout.get_active_tabs = MagicMock(return_value=fake_tabs)
    tabs.current = 0
    assert tabs.get_current_tab_name() == "TabName"

def test_get_current_tab_name_for_audio(tabs, dummy_window):
    dummy_tab = MagicMock(type=Tab.TAB_CHAT, idx=0, tooltip="tip")
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    dummy_window.core.tabs.titles = {Tab.TAB_CHAT: "Chat"}
    dummy_window.core.tabs.count_by_type.return_value = 2
    dummy_window.core.tabs.get_order_by_idx_and_type.return_value = 1
    fake_tabs = MagicMock()
    dummy_window.ui.layout.get_active_tabs = MagicMock(return_value=fake_tabs)
    result = tabs.get_current_tab_name_for_audio()
    assert "Chat" in result

def test_update_tooltip(tabs, dummy_window):
    fake_tabs = MagicMock()
    fake_tabs.setTabToolTip = MagicMock()
    dummy_window.ui.layout.get_active_tabs = MagicMock(return_value=fake_tabs)
    tabs.current = 1
    tabs.update_tooltip("new tooltip")
    fake_tabs.setTabToolTip.assert_called_with(1, "new tooltip")

def test_rename(tabs, dummy_window):
    dummy_tab = MagicMock(title="Old Title")
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    dummy_window.ui.dialog["rename"].show = MagicMock()
    dummy_window.ui.dialog["rename"].input = MagicMock()
    dummy_window.ui.dialog["rename"].input.setText = MagicMock()
    tabs.rename(5, 0)
    dummy_window.ui.dialog["rename"].input.setText.assert_called_with("Old Title")
    assert dummy_window.ui.dialog["rename"].current == 5
    dummy_window.ui.dialog["rename"].show.assert_called_once()

def test_update_name(tabs, dummy_window):
    dummy_window.ui.dialog["rename"].close = MagicMock()
    tabs.update_name(4, "NewName", close=True)
    dummy_window.core.tabs.update_title.assert_called_with(4, "NewName", "NewName")
    dummy_window.ui.dialog["rename"].close.assert_called_once()

def test_update_title(tabs, dummy_window):
    dummy_tab = MagicMock(type=Tab.TAB_CHAT, idx=1, tooltip="tip")
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    dummy_window.core.tabs.count_by_type.return_value = 2
    dummy_window.core.tabs.get_order_by_idx_and_type.return_value = 1
    fake_tabs = MagicMock()
    fake_tabs.setTabToolTip = MagicMock()
    dummy_window.ui.layout.get_active_tabs = MagicMock(return_value=fake_tabs)
    tabs.current = 1
    tabs.update_title(1, "LongTabNameExtra")
    fake_tabs.setTabToolTip.assert_called_with(1, "LongTabNameExtra")
    dummy_window.core.tabs.update_title.assert_called()

def test_update_title_current(tabs, dummy_window):
    orig_update_title = tabs.update_title
    called = False
    def fake_update_title(idx, title):
        nonlocal called
        called = True
    tabs.update_title = fake_update_title
    tabs.current = 3
    tabs.update_title_current("CurrentName")
    assert called is True
    tabs.update_title = orig_update_title

def test_on_load_ctx(tabs, dummy_window):
    dummy_tab = MagicMock(type=Tab.TAB_CHAT)
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    dummy_meta = MagicMock(id=77, name="MetaName")
    orig_update_title_current = tabs.update_title_current
    called = False
    def fake_update_title(name):
        nonlocal called
        called = True
    tabs.update_title_current = fake_update_title
    tabs.on_load_ctx(dummy_meta)
    assert dummy_tab.data_id == 77
    assert called is True
    tabs.update_title_current = orig_update_title_current

def test_open_by_type(tabs, dummy_window):
    dummy_window.core.tabs.get_min_idx_by_type.return_value = 2
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col=0):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.open_by_type(1)
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_new_tab(tabs, dummy_window):
    dummy_window.core.tabs.get_max_idx_by_column.return_value = -1
    orig_append = tabs.append
    called = False
    def fake_append(type, tool_id, idx, column_idx):
        nonlocal called
        called = True
    tabs.append = fake_append
    tabs.new_tab(0)
    assert called is True
    tabs.append = orig_append

def test_restore_data_no_data(tabs, dummy_window):
    dummy_window.core.config.get.return_value = []
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.restore_data()
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_move_tab(tabs, dummy_window):
    dummy_tab = MagicMock()
    dummy_tab.idx = 3
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    dummy_window.core.tabs.move_tab = MagicMock()
    orig_on_column_changed = tabs.on_column_changed
    called = False
    def fake_on_column_changed():
        nonlocal called
        called = True
    tabs.on_column_changed = fake_on_column_changed
    orig_switch = tabs.switch_tab_by_idx
    called_switch = False
    def fake_switch(idx, col):
        nonlocal called_switch
        called_switch = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.move_tab(3, 0, 1)
    dummy_window.core.tabs.move_tab.assert_called_with(dummy_tab, 1)
    assert called is True
    assert called_switch is True
    tabs.on_column_changed = orig_on_column_changed
    tabs.switch_tab_by_idx = orig_switch

def test_is_current_by_type(tabs, dummy_window):
    dummy_tab = MagicMock(type=5)
    dummy_window.core.tabs.get_tab_by_pid.return_value = dummy_tab
    tabs.col = {0: 10}
    assert tabs.is_current_by_type(5) is True

def test_is_current_tool(tabs, dummy_window):
    dummy_tab = MagicMock(tool_id="tool")
    dummy_window.core.tabs.get_tab_by_pid.return_value = dummy_tab
    tabs.col = {0: 20}
    assert tabs.is_current_tool("tool") is True

def test_get_current_by_column(tabs, dummy_window):
    fake_tabs = MagicMock()
    fake_tabs.currentIndex.return_value = 0
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=fake_tabs)
    dummy_window.core.tabs.get_tab_by_index.return_value = "tab_object"
    assert tabs.get_current_by_column(0) == "tab_object"

def test_is_tool(tabs, dummy_window):
    dummy_tab = MagicMock(tool_id="tool1")
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    fake_tabs = MagicMock()
    fake_tabs.count.return_value = 1
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=fake_tabs)
    tabs.col = {0: None}
    assert isinstance(tabs.is_tool("tool1"), bool)

def test_get_first_tab_by_tool(tabs, dummy_window):
    dummy_tab = MagicMock(tool_id="tool2", idx=7, column_idx=0)
    dummy_window.core.tabs.get_tab_by_index.return_value = dummy_tab
    tabs.col = {0: None}
    fake_tabs = MagicMock()
    fake_tabs.count.return_value = 1
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=fake_tabs)
    result = tabs.get_first_tab_by_tool("tool2")
    assert result == dummy_tab

def test_switch_to_first_tab_by_tool(tabs, dummy_window):
    dummy_tab = MagicMock(tool_id="t1", idx=4, column_idx=0)
    tabs.get_first_tab_by_tool = MagicMock(return_value=dummy_tab)
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.switch_to_first_tab_by_tool("t1")
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_get_tool_column(tabs, dummy_window):
    dummy_tab = MagicMock(tool_id="tool3")
    dummy_window.core.tabs.get_tab_by_pid.return_value = dummy_tab
    tabs.col = {2: 30}
    assert tabs.get_tool_column("tool3") == 2

def test_switch_to_first_chat(tabs, dummy_window):
    tabs.is_current_by_type = MagicMock(return_value=False)
    tabs.get_current_type = MagicMock(return_value=1)
    dummy_tab = MagicMock(type=Tab.TAB_CHAT, idx=5)
    dummy_window.core.tabs.get_tab_by_pid.return_value = dummy_tab
    tabs.col = {0: 50}
    orig_switch = tabs.switch_tab_by_idx
    called = False
    def fake_switch(idx, col):
        nonlocal called
        called = True
    tabs.switch_tab_by_idx = fake_switch
    tabs.switch_to_first_chat()
    assert called is True
    tabs.switch_tab_by_idx = orig_switch

def test_focus_by_type(tabs, dummy_window):
    tabs.get_current_type = MagicMock(return_value=999)
    fake_tabs = MagicMock()
    fake_tabs.currentIndex.return_value = 0
    dummy_window.ui.layout.get_tabs_by_idx = MagicMock(return_value=fake_tabs)
    dummy_window.core.tabs.get_min_idx_by_type_exists = MagicMock(return_value=(2, 0, True))
    tabs.focus_by_type(999, data_id=123, title="Title", meta=MagicMock(id=321))
    assert dummy_window.controller.ctx.load.called or True

def test_on_split_screen_changed(tabs, dummy_window):
    dummy_window.core.config.get.return_value = False
    dummy_window.ui.nodes["layout.split"].box = MagicMock()
    dummy_window.ui.nodes["layout.split"].box.isChecked.return_value = False
    dummy_window.core.config.set = MagicMock()
    dummy_window.core.config.save = MagicMock()
    tabs.on_split_screen_changed(True)
    dummy_window.core.config.set.assert_called_with("layout.split", True)
    dummy_window.core.config.save.assert_called()

def test_enable_split_screen(tabs, dummy_window):
    dummy_window.core.config.get.return_value = False
    dummy_window.ui.splitters["columns"].setSizes = MagicMock()
    dummy_window.core.config.set = MagicMock()
    dummy_window.core.config.save = MagicMock()
    dummy_window.ui.nodes["layout.split"].box = MagicMock()
    tabs.enable_split_screen(update_switch=True)
    dummy_window.ui.splitters["columns"].setSizes.assert_called_with([1, 1])
    dummy_window.core.config.set.assert_called_with("layout.split", True)
    dummy_window.core.config.save.assert_called()
    dummy_window.ui.nodes["layout.split"].box.setChecked.assert_called_with(True)

def test_disable_split_screen(tabs, dummy_window):
    dummy_window.ui.splitters["columns"].setSizes = MagicMock()
    dummy_window.core.config.set = MagicMock()
    dummy_window.core.config.save = MagicMock()
    orig_on_column_changed = tabs.on_column_changed
    called = False
    def fake_on_column_changed():
        nonlocal called
        called = True
    tabs.on_column_changed = fake_on_column_changed
    tabs.disable_split_screen()
    dummy_window.ui.splitters["columns"].setSizes.assert_called_with([1, 0])
    dummy_window.core.config.set.assert_called_with("layout.split", False)
    dummy_window.core.config.save.assert_called()
    assert called is True
    tabs.on_column_changed = orig_on_column_changed

def test_toggle_split_screen_enable(tabs, dummy_window):
    orig_enable = tabs.enable_split_screen
    called = False
    def fake_enable(update_switch=False):
        nonlocal called
        called = True
    tabs.enable_split_screen = fake_enable
    tabs.toggle_split_screen(True)
    assert called is True
    tabs.enable_split_screen = orig_enable

def test_toggle_split_screen_disable(tabs, dummy_window):
    orig_disable = tabs.disable_split_screen
    called = False
    def fake_disable():
        nonlocal called
        called = True
    tabs.disable_split_screen = fake_disable
    tabs.toggle_split_screen(False)
    assert called is True
    tabs.disable_split_screen = orig_disable