# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 17:00:00                  #
# ================================================== #
from PySide6.QtCore import QTimer

from pygpt_net.core.access.events import AppEvent
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

    def setup(self):
        """Setup tabs"""
        self.window.core.tabs.load()
        self.window.controller.notepad.load()
        self.initialized = True

    def add(self, type: int, title: str, icon=None, reference=None, data_id=None):
        """
        Add tab

        :param type: Tab type
        :param title: Tab title
        :param icon: Tab icon
        :param reference: Tab reference
        :param data_id: Tab data ID
        """
        self.window.core.tabs.add(type, title, icon, reference, data_id)

    def append(self, type: int, idx: int):
        """
        Append tab in place

        :param type: Tab type
        :param idx: Tab index
        """
        self.appended = True  # lock reload in previous tab
        self.window.core.tabs.append(type, idx)
        self.switch_tab_by_idx(idx + 1)  # switch to new tab

    def reload_titles(self):
        """Reload tab titles"""
        self.window.core.tabs.reload_titles()

    def reload(self):
        """Reload tabs"""
        self.window.core.tabs.reload()
        self.window.controller.chat.render.prepare()

    def reload_after(self):
        """Reload tabs after"""
        for pid in self.window.ui.nodes['output']:
            if self.window.core.config.get("render.plain") is True:
                self.window.ui.nodes['output_plain'][pid].setVisible(True)
                self.window.ui.nodes['output'][pid].setVisible(False)
            else:
                self.window.ui.nodes['output_plain'][pid].setVisible(False)
                self.window.ui.nodes['output'][pid].setVisible(True)
        self.switch_tab(Tab.TAB_CHAT)

    def on_tab_changed(self, idx: int):
        """
        Output tab changed

        :param idx: tab index
        """
        tab = self.window.core.tabs.get_tab_by_index(idx)
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
        self.current = idx
        self.window.controller.ui.mode.update()
        self.window.controller.ui.vision.update()

        # check type
        if tab.type == Tab.TAB_NOTEPAD:
            self.window.controller.notepad.opened_once = True
            self.window.controller.notepad.on_open(idx)
        elif tab.type == Tab.TAB_CHAT:
            pid_meta = self.window.core.ctx.output.get_meta(tab.pid)
            meta = self.window.core.ctx.get_meta_by_id(pid_meta)
            if meta is not None:
                self.window.controller.ctx.load(pid_meta)  # reload renderer
        elif tab.type == Tab.TAB_TOOL_PAINTER:
            if self.window.core.config.get('vision.capture.enabled'):
                self.window.controller.camera.enable_capture()

        if prev_tab != idx:
            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.TAB_SELECTED))  # app event

    def get_current_idx(self) -> int:
        """
        Get current tab index

        :return: tab index
        """
        return self.current

    def get_current_tab(self) -> Tab or None:
        """
        Get current tab

        :return: tab
        """
        return self.window.core.tabs.get_tab_by_index(self.current)

    def get_current_type(self) -> int or None:
        """
        Get current tab type

        :return: tab type
        """
        tab = self.window.core.tabs.get_tab_by_index(self.current)
        if tab is None:
            return None
        return tab.type

    def get_current_pid(self) -> int or None:
        """
        Get current tab PID

        :return: tab PID
        """
        tab = self.window.core.tabs.get_tab_by_index(self.current)
        if tab is None:
            return None
        return tab.pid

    def get_type_by_idx(self, idx: int) -> int or None:
        """
        Get tab type by index

        :param idx: tab index
        :return: tab type
        """
        tab = self.window.core.tabs.get_tab_by_index(idx)
        if tab is None:
            return None
        return tab.type

    def get_first_idx_by_type(self, type: int) -> int or None:
        """
        Get first tab index by type

        :param type: tab type
        :return: tab index
        """
        return self.window.core.tabs.get_min_idx_by_type(type)

    def on_tab_clicked(self, idx: int):
        """
        Tab click event

        :param idx: tab index
        """
        pass

    def on_tab_dbl_clicked(self, idx: int):
        """
        Tab double click event

        :param idx: tab index
        """
        pass

    def on_tab_closed(self, idx: int):
        """
        Tab close event

        :param idx: tab index
        """
        self.window.core.tabs.remove_tab_by_idx(idx)

    def on_tab_moved(self, idx: int):
        """
        Tab moved event

        :param idx: tab index
        """
        self.window.core.tabs.update()

    def close(self, idx: int):
        """
        Close tab

        :param idx: tab index
        """
        self.on_tab_closed(idx)

    def close_all(self, type: int, force: bool = False):
        """
        Close all tabs

        :param type: tab type
        :param force: force close
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='tab.close_all',
                id=type,
                msg=trans('tab.close_all.confirm'),
            )
            return
        self.window.core.tabs.remove_all_by_type(type)

    def next_tab(self):
        """Switch to next tab"""
        current = self.window.ui.tabs['output'].currentIndex()
        all = len(self.window.ui.tabs['output'].children())
        next = current + 1
        if next >= all:
            next = 0
        self.switch_tab_by_idx(next)

    def prev_tab(self):
        """Switch to previous tab"""
        current = self.window.ui.tabs['output'].currentIndex()
        all = len(self.window.ui.tabs['output'].children())
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

    def switch_tab_by_idx(self, idx: int):
        """
        Switch tab by index

        :param idx: tab index
        """
        self.window.ui.tabs['output'].setCurrentIndex(idx)
        self.on_tab_changed(idx)

    def get_current_tab_name(self) -> str:
        """
        Get current tab name

        :return: tab name
        """
        return self.window.ui.tabs['output'].tabText(self.current)

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

        :param tooltip: tooltip
        """
        self.window.ui.tabs['output'].setTabToolTip(self.current, tooltip)

    def rename(self, idx: int):
        """
        Rename tab

        :param idx: tab idx
        """
        # get tab
        tab = self.window.core.tabs.get_tab_by_index(idx)
        if tab is None:
            return
        # set dialog and show
        self.window.ui.dialog['rename'].id = 'tab'
        self.window.ui.dialog['rename'].input.setText(tab.title)
        self.window.ui.dialog['rename'].current = idx
        self.window.ui.dialog['rename'].show()

    def update_name(self, idx: int, name: str, close: bool = True):
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

    def update_title(self, idx: int, title: str):
        """
        Update tab title

        :param idx: tab idx
        :param title: new title
        """
        # check if current tab is chat
        if self.get_current_type() != Tab.TAB_CHAT:
            return
        tooltip = title
        self.window.ui.tabs['output'].setTabToolTip(idx, tooltip)
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

    def new_tab(self):
        """Handle [+} button"""
        idx = self.get_current_idx()
        self.append(Tab.TAB_CHAT, idx)
