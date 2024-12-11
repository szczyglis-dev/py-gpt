# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.09 23:00:00                  #
# ================================================== #

from PySide6.QtCore import QTimer

from pygpt_net.core.events import AppEvent, RenderEvent
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class Tabs:
    def __init__(self, window=None):
        """
        UI tabs controller

        :param window: Window instance
        """
        self.window = window
        self.active_idx = 0
        self.prev_idx = 0
        self.initialized = False
        self.appended = False
        self.current = 0
        self.column_idx = 0
        self.tmp_column_idx = 0
        self.locked = False

    def setup(self):
        """Setup tabs"""
        self.window.core.tabs.load()
        self.window.controller.notepad.load()
        self.setup_options()
        self.initialized = True

    def setup_options(self):
        """Setup options"""
        state = self.window.core.config.get("layout.split", False)
        self.window.ui.nodes['layout.split'].setChecked(state)
        if not state:
            self.window.ui.splitters['columns'].setSizes([1, 0])

    def add(
            self,
            type: int,
            title: str,
            icon=None,
            child=None,
            data_id=None,
            tool_id=None,
    ):
        """
        Add a new tab

        :param type: Tab type
        :param title: Tab title
        :param icon: Tab icon
        :param child: Tab child (child widget)
        :param data_id: Tab data ID (child data ID)
        :param tool_id: Tool ID
        """
        self.window.core.tabs.add(
            type=type,
            title=title,
            icon=icon,
            child=child,
            data_id=data_id,
            tool_id=tool_id
        )

    def append(
            self,
            type: int,
            tool_id: str = None,
            idx: int = 0,
            column_idx: int = 0
    ):
        """
        Append tab at tab index

        :param type: Tab type
        :param tool_id: Tool ID
        :param idx: Tab index
        :param column_idx: Column index
        """
        self.appended = True  # lock reload in previous tab
        self.column_idx = column_idx  # switch to column
        self.window.core.tabs.append(
            type=type,
            idx=idx,
            column_idx=column_idx,
            tool_id=tool_id
        )
        self.switch_tab_by_idx(idx + 1, column_idx)  # switch to new tab

    def reload_titles(self):
        """Reload tab titles"""
        self.window.core.tabs.reload_titles()

    def reload(self):
        """Reload tabs"""
        self.window.core.tabs.reload()
        event = RenderEvent(RenderEvent.PREPARE)
        self.window.dispatch(event)

    def reload_after(self):
        """Reload tabs after"""
        for pid in self.window.ui.nodes['output']:
            if self.window.core.config.get("render.plain") is True:
                self.window.ui.nodes['output_plain'][pid].setVisible(True)
                self.window.ui.nodes['output'][pid].setVisible(False)
            else:
                self.window.ui.nodes['output_plain'][pid].setVisible(False)
                self.window.ui.nodes['output'][pid].setVisible(True)
        #self.switch_tab(Tab.TAB_CHAT)

    def on_tab_changed(self, idx: int, column_idx: int = 0):
        """
        Output tab changed

        :param idx: tab index
        :param column_idx: column index
        """
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None:
            self.appended = False
            return

        if self.appended:
            self.appended = False
            if tab.type == Tab.TAB_CHAT:
                self.current = idx
                meta = self.window.controller.ctx.new()  # new context
                if meta is not None:
                    self.window.controller.ctx.load(meta.id)  # reload

        prev_tab = self.current
        prev_column = self.column_idx
        self.current = idx
        self.column_idx = column_idx
        self.window.controller.ui.mode.update()
        self.window.controller.ui.vision.update()

        # check type
        if tab.type == Tab.TAB_NOTEPAD:
            self.window.controller.notepad.opened_once = True
            self.window.controller.notepad.on_open(idx, column_idx)
        elif tab.type == Tab.TAB_CHAT:
            # get meta for selected tab, if not loaded yet then append meta here
            meta_id = self.window.core.ctx.output.prepare_meta(tab)
            meta = self.window.core.ctx.get_meta_by_id(meta_id)
            if meta is not None:
                self.window.controller.ctx.load(meta.id)  # reload renderer
        elif tab.type == Tab.TAB_TOOL_PAINTER:
            if self.window.core.config.get('vision.capture.enabled'):
                self.window.controller.camera.enable_capture()

        if prev_tab != idx or prev_column != column_idx:
            self.window.dispatch(AppEvent(AppEvent.TAB_SELECTED))  # app event

    def get_current_idx(self, column_idx: int = 0) -> int:
        """
        Get current tab index

        :param column_idx: column index
        :return: tab index
        """
        return self.current

    def get_current_column_idx(self) -> int:
        """
        Get current column index

        :return: column index
        """
        return self.column_idx

    def get_current_tab(self) -> Tab or None:
        """
        Get current tab

        :return: tab
        """
        return self.window.core.tabs.get_tab_by_index(self.get_current_idx(), self.column_idx)

    def get_current_type(self) -> int or None:
        """
        Get current tab type

        :return: tab type
        """
        tab = self.window.core.tabs.get_tab_by_index(self.get_current_idx(), self.column_idx)
        if tab is None:
            return None
        return tab.type

    def get_current_pid(self) -> int or None:
        """
        Get current tab PID

        :return: tab PID
        """
        tab = self.window.core.tabs.get_tab_by_index(self.get_current_idx(), self.column_idx)
        if tab is None:
            return None
        return tab.pid

    def get_type_by_idx(self, idx: int) -> int or None:
        """
        Get tab type by index

        :param idx: tab index
        :return: tab type
        """
        tab = self.window.core.tabs.get_tab_by_index(idx, self.column_idx)
        if tab is None:
            return None
        return tab.type

    def get_first_idx_by_type(self, type: int) -> int or None:
        """
        Get first tab index by type

        :param type: tab type
        :return: tab index
        """
        return self.window.core.tabs.get_min_idx_by_type(type, self.column_idx)

    def on_column_changed(self):
        """Column changed event"""
        if self.locked:
            return
        tab = self.window.core.tabs.get_tab_by_index(self.current, self.column_idx)
        if tab is None:
            return
        current_ctx = self.window.core.ctx.get_current()
        if current_ctx is not None and current_ctx != tab.data_id:
            self.window.controller.ctx.select_on_list_only(tab.data_id)

    def on_tab_clicked(self, idx: int, column_idx: int = 0):
        """
        Tab click event

        :param idx: tab index
        :param column_idx: column index
        """
        self.current = idx
        self.column_idx = column_idx
        self.on_column_changed()

    def on_column_focus(self, idx: int):
        """
        Column focus event

        :param idx: column index
        """
        self.column_idx = idx
        self.on_column_changed()

    def on_tab_dbl_clicked(self, idx: int, column_idx: int = 0):
        """
        Tab double click event

        :param idx: tab index
        :param column_idx: column index
        """
        self.column_idx = column_idx
        self.on_tab_changed(idx, column_idx)

    def on_tab_closed(self, idx: int, column_idx: int = 0):
        """
        Tab close event

        :param idx: tab index
        :param column_idx: column index
        """
        self.window.core.tabs.remove_tab_by_idx(idx, column_idx)

    def on_tab_moved(self, idx: int, column_idx: int = 0):
        """
        Tab moved event

        :param idx: tab index
        :param column_idx: column index
        """
        self.window.core.tabs.update()

    def close(self, idx: int, column_idx: int = 0):
        """
        Close tab

        :param idx: tab index
        :param column_idx: column index
        """
        self.on_tab_closed(idx, column_idx)

    def close_all(
            self,
            type: int,
            column_idx: int = 0,
            force: bool = False
    ):
        """
        Close all tabs

        :param type: tab type
        :param column_idx: column index
        :param force: force close
        """
        if not force:
            self.tmp_column_idx = column_idx
            self.window.ui.dialogs.confirm(
                type='tab.close_all',
                id=type,
                msg=trans('tab.close_all.confirm'),
            )
            return
        column_idx = self.tmp_column_idx
        self.window.core.tabs.remove_all_by_type(type, column_idx)

    def next_tab(self):
        """Switch to next tab"""
        tabs = self.window.ui.layout.get_active_tabs()
        current = tabs.currentIndex()
        all = len(tabs.children())
        next = current + 1
        if next >= all:
            next = 0
        self.switch_tab_by_idx(next)

    def prev_tab(self):
        """Switch to previous tab"""
        tabs = self.window.ui.layout.get_active_tabs()
        current = tabs.currentIndex()
        all = len(tabs.children())
        prev = current - 1
        if prev < 0:
            prev = all - 1
        self.switch_tab_by_idx(prev)

    def switch_tab(self, type: int):
        """
        Switch tab

        :param type: tab type
        """
        idx = self.window.core.tabs.get_min_idx_by_type(type)
        if idx is not None:
            self.switch_tab_by_idx(idx)

    def switch_tab_by_idx(self, idx: int, column_idx: int = 0):
        """
        Switch tab by index

        :param idx: tab index
        :param column_idx: column index
        """
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        tabs.setCurrentIndex(idx)
        self.on_tab_changed(idx, column_idx)

    def get_current_tab_name(self) -> str:
        """
        Get current tab name

        :return: tab name
        """
        tabs = self.window.ui.layout.get_active_tabs()
        return tabs.tabText(self.current)

    def get_current_tab_name_for_audio(self) -> str:
        """
        Get current tab name for audio description

        :return: tab name
        """
        tab = self.get_current_tab()
        if tab is None:
            return ""

        title = ""
        if tab.type in self.window.core.tabs.titles:
            title = trans(self.window.core.tabs.titles[tab.type])

        # if more than 1 with this type then attach position info
        num = self.window.core.tabs.count_by_type(tab.type)
        if num > 1:
            order = self.window.core.tabs.get_order_by_idx_and_type(tab.idx, tab.type)
            if order != -1:
                title += " #" + str(order)
        if tab.tooltip is not None and tab.tooltip != "":
            title += " - " + tab.tooltip
        return title

    def update_tooltip(self, tooltip: str):
        """
        Update tab tooltip

        :param tooltip: tooltip text
        """
        tabs = self.window.ui.layout.get_active_tabs()
        tabs.setTabToolTip(self.current, tooltip)

    def rename(self, idx: int, column_idx: int = 0):
        """
        Rename tab (show dialog)

        :param idx: tab idx
        :param column_idx: column idx
        """
        # get tab
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None:
            return
        # set dialog and show
        self.window.ui.dialog['rename'].id = 'tab'
        self.window.ui.dialog['rename'].input.setText(tab.title)
        self.window.ui.dialog['rename'].current = idx
        self.window.ui.dialog['rename'].show()

    def update_name(
            self,
            idx: int,
            name: str,
            close: bool = True
    ):
        """
        Update tab title

        :param idx: tab idx
        :param name: new title
        :param close: close dialog
        """
        self.window.core.tabs.update_title(idx, name)
        if close:
            self.window.ui.dialog['rename'].close()

    def update_current_name(self, name: str):
        """
        Update current tab title

        :param name: new title
        """
        self.update_name(self.current, name)

    def update_title(
            self,
            idx: int,
            title: str
    ):
        """
        Update tab title

        :param idx: tab idx
        :param title: new title
        """
        # check if current tab is chat
        if self.get_current_type() != Tab.TAB_CHAT:
            return
        tabs = self.window.ui.layout.get_active_tabs()
        tooltip = title
        tabs.setTabToolTip(idx, tooltip)
        if len(title) > 8:
            title = title[:8] + '...'  # truncate to max 8 chars
        self.window.core.tabs.update_title(idx, title, tooltip)

    def update_title_current(self, title: str):
        """
        Update current tab title

        :param title: new title
        """
        self.update_title(self.current, title)

    def open_by_type(self, type: int):
        """
        Open first tab by type

        :param type: tab type
        """
        idx = self.window.core.tabs.get_min_idx_by_type(type)
        if idx is not None:
            self.switch_tab_by_idx(idx)

    def new_tab(self, column_idx: int = 0):
        """
        Handle [+] button

        :param column_idx: column index
        """
        idx = self.get_current_idx(column_idx)
        self.append(
            type=Tab.TAB_CHAT,
            tool_id=None,
            idx=idx,
            column_idx=column_idx
        )

    def restore_data(self):
        """Restore tab data"""
        data = self.window.core.config.get("tabs.opened", [])
        if not data:
            self.switch_tab_by_idx(0, 0)
            return
        for col_idx in data:
            tab_idx = data[col_idx]
            self.switch_tab_by_idx(int(tab_idx), int(col_idx))

        # set default column to 0
        self.column_idx = 0
        self.on_column_changed()

    def move_tab(self, idx: int, column_idx: int, new_column_idx: int):
        """
        Move tab to another column

        :param idx: tab index
        :param column_idx: column index
        :param new_column_idx: new column index
        """
        self.locked = True
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        self.window.core.tabs.move_tab(tab, new_column_idx)
        self.locked = False

    def toggle_split_screen(self, state):
        """
        Toggle split screen

        :param state: state
        """
        if state:
            #self.rightWidget.show()
            self.window.ui.splitters['columns'].setSizes([1, 1])
        else:
            #self.rightWidget.hide()
            self.window.ui.splitters['columns'].setSizes([1, 0])
        self.window.core.config.set("layout.split", state)
        self.window.core.config.save()
