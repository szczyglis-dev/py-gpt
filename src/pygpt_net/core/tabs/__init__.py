#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.11 04:00:00                  #
# ================================================== #

import uuid
from datetime import datetime

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLayout

from .tab import Tab
from pygpt_net.ui.widget.tabs.body import TabBody
from pygpt_net.utils import trans


class Tabs:

    # types
    TAB_ADD = -1
    TAB_CHAT = 0
    TAB_NOTEPAD = 1
    TAB_FILES = 2
    TAB_TOOL_PAINTER = 3
    TAB_TOOL_CALENDAR = 4

    def __init__(self, window=None):
        """
        Tabs core

        :param window: Window instance
        """
        self.window = window
        self.last_pid = -1
        self.pids = {}  # pid: Tab data
        self.icons = {
            self.TAB_CHAT: ":/icons/chat.svg",
            self.TAB_NOTEPAD: ":/icons/paste.svg",
            self.TAB_FILES: ":/icons/folder_filled.svg",
            self.TAB_TOOL_PAINTER: ":/icons/brush.svg",
            self.TAB_TOOL_CALENDAR: ":/icons/calendar.svg",
        }
        self.titles = {
            self.TAB_CHAT: "output.tab.chat",
            self.TAB_NOTEPAD: "output.tab.notepad",
            self.TAB_FILES: "output.tab.files",
            self.TAB_TOOL_PAINTER: "output.tab.painter",
            self.TAB_TOOL_CALENDAR: "output.tab.calendar",
        }

    def get_tab_by_index(self, idx: int) -> Tab or None:
        """
        Get tab by index

        :param idx: Tab index
        :return: Tab
        """
        tab = self.window.ui.tabs['output'].widget(idx)
        if tab is None:
            return None
        return tab.getOwner()

    def get_tab_by_pid(self, pid: int) -> Tab or None:
        """
        Get tab by PID

        :param pid: PID
        :return: Tab
        """
        if pid in self.pids:
            return self.pids[pid]
        return None

    def get_first_tab_by_type(self, type: int) -> Tab or None:
        """
        Get first tab by type

        :param type: Tab type
        :return: Tab
        """
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.type == type:
                return tab
        return None

    def get_active_pid(self) -> int or None:
        """
        Get PID by active tab

        :return: PID
        """
        tab = self.get_tab_by_index(self.window.ui.tabs['output'].currentIndex())
        if tab is None:
            return 0
        return tab.pid

    def add(self, type: int, title: str, icon=None, reference=None, data_id=None) -> Tab:
        """
        Add tab

        :param type: Tab type
        :param title: Tab title
        :param icon: Tab icon
        :param reference: Tab reference
        :param data_id: Tab data ID
        :return: Tab
        """
        self.last_pid += 1  # PID++, start from 0

        tab = Tab()
        tab.uuid = uuid.uuid4()
        tab.pid = self.last_pid
        tab.type = type
        tab.title = title
        tab.icon = icon
        tab.reference = reference
        tab.data_id = data_id

        if type == Tab.TAB_CHAT:
            self.add_chat(tab)
        elif type == Tab.TAB_NOTEPAD:
            self.add_notepad(tab)
        elif type == Tab.TAB_FILES:
            self.add_tool_explorer(tab)
        elif type == Tab.TAB_TOOL_PAINTER:
            self.add_tool_painter(tab)
        elif type == Tab.TAB_TOOL_CALENDAR:
            self.add_tool_calendar(tab)

        self.pids[tab.pid] = tab
        return tab

    def append(self, type: int, idx: int) -> Tab:
        """
        Append tab to the right side of the tab with the specified index

        :param type: tab type
        :param idx: index of the tab to the right of which the new tab will be added
        :return: Tab
        """
        self.last_pid += 1  # PID++, start from 0
        title = ""
        icon = self.icons[type]
        if type == self.TAB_CHAT:
            title = trans('output.tab.chat') + " {}".format(self.count_by_type(type) + 1)
        elif type == self.TAB_NOTEPAD:
            title = trans('output.tab.notepad') + " {}".format(self.count_by_type(type) + 1)

        tab = Tab()
        tab.uuid = uuid.uuid4()
        tab.pid = self.last_pid
        tab.type = type
        tab.title = title
        tab.icon = icon
        tab.new_idx = idx + 1  # place on right side

        if type == Tab.TAB_CHAT:
            self.add_chat(tab)
        elif type == Tab.TAB_NOTEPAD:
            self.add_notepad(tab)

        self.pids[tab.pid] = tab
        self.update()

        # load data from db
        if type == Tab.TAB_NOTEPAD:
            self.window.controller.notepad.load()
        return tab

    def restore(self, data: dict):
        """
        Restore tab from saved data

        :param data: Tab data
        """
        tab = Tab()
        tab.uuid = data["uuid"]
        tab.pid = data["pid"]
        tab.type = data["type"]
        tab.title = data["title"]
        tab.data_id = data["data_id"]
        tab.reference = None

        if 'tooltip' in data and data['tooltip'] is not None:
            tab.tooltip = data['tooltip']

        if tab.type in self.icons:
            tab.icon = self.icons[tab.type]

        if tab.type == Tab.TAB_CHAT:  # chat
            self.add_chat(tab)
            self.window.core.ctx.output.mapping[tab.pid] = tab.data_id  # restore pid => meta.id mapping
            self.window.core.ctx.output.last_pids[tab.data_id] = tab.pid
            self.window.core.ctx.output.last_pid = tab.pid
        elif tab.type == Tab.TAB_NOTEPAD: # notepad
            self.add_notepad(tab)
        elif tab.type == Tab.TAB_FILES:  # files
            self.add_tool_explorer(tab)
        elif tab.type == Tab.TAB_TOOL_PAINTER:  # painter
            self.add_tool_painter(tab)
        elif tab.type == Tab.TAB_TOOL_CALENDAR:  # calendar
            self.add_tool_calendar(tab)

        self.pids[tab.pid] = tab
        self.last_pid = self.get_max_pid()

    def remove_tab_by_idx(self, idx: int):
        """
        Remove tab by index

        :param idx: Tab index
        """
        tab = self.get_tab_by_index(idx)
        if tab is None:
            return
        self.remove(tab.pid)

    def remove(self, pid: int):
        """
        Remove tab by PID

        :param pid: PID
        """
        tab = self.get_tab_by_pid(pid)
        if tab is None:
            return
        self.window.ui.tabs['output'].removeTab(tab.idx)
        del self.pids[pid]
        self.update()

    def remove_all(self):
        """Remove all tabs"""
        for pid in list(self.pids):
            self.remove(pid)  # delete from PIDs and UI
        self.window.core.ctx.output.clear()  # clear mapping

    def remove_all_by_type(self, type: int):
        """
        Remove all tabs by type

        :param type: Tab type
        """
        for pid in list(self.pids):
            tab = self.pids[pid]
            if tab.type == type:
                if type == self.TAB_CHAT:
                    if self.count_by_type(type) == 1:
                        continue  # do not remove last chat tab
                self.remove(pid)

    def reload(self):
        """Reload tabs"""
        self.remove_all()
        self.load()

    def get_tabs_by_type(self, type: int) -> list:
        """
        Get tabs by type

        :param type: Tab type
        :return: List of tabs
        """
        tabs = []
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.type == type:
                tabs.append(tab)
        return tabs

    def get_min_pid(self) -> int:
        """
        Get min PID

        :return: Min PID
        """
        min = 999999
        for pid in self.pids:
            if pid < min:
                min = pid
        return min

    def get_max_pid(self) -> int:
        """
        Get max PID

        :return: Max PID
        """
        max = 0
        for pid in self.pids:
            if pid > max:
                max = pid
        return max

    def count_by_type(self, type: int) -> int:
        """
        Count tabs by type

        :param type: Tab type
        :return: Number of tabs
        """
        count = 0
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.type == type:
                count += 1
        return count

    def get_order_by_idx_and_type(self, idx: int, type: int) -> int:
        """
        Get the order of the tab by index and type

        :param idx: Tab index
        :param type: Tab type
        :return: Order of the tab (starting from 1)
        """
        tabs_of_type = [tab for tab in self.pids.values() if tab.type == type]
        tabs_of_type.sort(key=lambda tab: tab.idx)

        for order, tab in enumerate(tabs_of_type, start=1):
            if tab.idx == idx:
                return order
        return -1  # Return -1 if the tab with the specified index and type is not found

    def get_min_idx_by_type(self, type: int) -> int:
        """
        Get min index by type

        :param type: Tab type
        :return: Min index
        """
        min = 999999
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.type == type and tab.idx < min:
                min = tab.idx
        return min

    def update(self):
        """Update tabs data (pids) from UI"""
        for pid in self.pids:
            tab = self.pids[pid]
            tab.idx = self.window.ui.tabs['output'].indexOf(tab.reference)
            tab.title = self.window.ui.tabs['output'].tabText(tab.idx)
            tab.tooltip = self.window.ui.tabs['output'].tabToolTip(tab.idx)
            tab.updated_at = datetime.now()

    def add_chat(self, tab: Tab):
        """
        Add chat tab

        :param tab: Tab instance
        """
        tab.reference = self.window.core.ctx.container.register_output(tab.pid)
        if tab.new_idx is not None:
            tab.idx = self.window.ui.tabs['output'].insertTab(tab.new_idx, tab.reference, tab.title)
        else:
            tab.idx = self.window.ui.tabs['output'].addTab(tab.reference, tab.title)
        tab.reference.setOwner(tab)
        self.window.ui.tabs['output'].setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            self.window.ui.tabs['output'].setTabToolTip(tab.idx, tab.tooltip)

    def add_notepad(self, tab: Tab):
        """
        Add notepad tab

        :param tab: Tab instance
        """
        idx = None
        if tab.data_id is not None:
            idx = tab.data_id  # restore prev idx
        tab.reference, idx = self.window.controller.notepad.create(idx)
        tab.data_id = idx  # notepad idx in db, enumerated from 1
        if tab.new_idx is not None:
            tab.idx = self.window.ui.tabs['output'].insertTab(tab.new_idx, tab.reference, tab.title)
        else:
            tab.idx = self.window.ui.tabs['output'].addTab(tab.reference, tab.title)
        tab.reference.setOwner(tab)
        self.window.ui.tabs['output'].setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            self.window.ui.tabs['output'].setTabToolTip(tab.idx, tab.tooltip)

    def add_tool_explorer(self, tab: Tab):
        """
        Add explorer tab

        :param tab: Tab instance
        """
        tab.reference = self.window.ui.chat.output.explorer.setup()
        tab.idx = self.window.ui.tabs['output'].addTab(tab.reference, tab.title)
        tab.reference.setOwner(tab)
        self.window.ui.tabs['output'].setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            self.window.ui.tabs['output'].setTabToolTip(tab.idx, tab.tooltip)

    def add_tool_painter(self, tab: Tab):
        """
        Add painter tab

        :param tab: Tab instance
        """
        tab.reference = self.window.ui.chat.output.painter.setup()
        tab.idx = self.window.ui.tabs['output'].addTab(tab.reference, tab.title)
        tab.reference.setOwner(tab)
        self.window.ui.tabs['output'].setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            self.window.ui.tabs['output'].setTabToolTip(tab.idx, tab.tooltip)

    def add_tool_calendar(self, tab: Tab):
        """
        Add calendar tab

        :param tab: Tab instance
        """
        tab.reference = self.window.ui.chat.output.calendar.setup()
        tab.idx = self.window.ui.tabs['output'].addTab(tab.reference, tab.title)
        tab.reference.setOwner(tab)
        self.window.ui.tabs['output'].setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            self.window.ui.tabs['output'].setTabToolTip(tab.idx, tab.tooltip)

    def get_first_by_type(self, type: int) -> Tab or None:
        """
        Get first tab by type

        :param type: Tab type
        :return: Tab
        """
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.type == type:
                return tab
        return None

    def from_defaults(self) -> dict:
        """
        Prepare default tabs data

        :return: Dict with tabs data
        """
        data = {}
        data[0] = {
            "uuid": uuid.uuid4(),
            "pid": 0,
            "idx": 0,
            "type": self.TAB_CHAT,
            "data_id": None,
            "title": "Chat",
            "tooltip": "Chat",
        }
        data[1] = {
            "uuid": uuid.uuid4(),
            "pid": 1,
            "idx": 1,
            "type": self.TAB_FILES,
            "data_id": None,
            "title": "Files",
            "tooltip": "Files",
        }
        data[2] = {
            "uuid": uuid.uuid4(),
            "pid": 2,
            "idx": 2,
            "type": self.TAB_TOOL_CALENDAR,
            "data_id": None,
            "title": "Calendar",
            "tooltip": "Calendar",
        }
        data[3] = {
            "uuid": uuid.uuid4(),
            "pid": 3,
            "idx": 3,
            "type": self.TAB_TOOL_PAINTER,
            "data_id": None,
            "title": "Painter",
            "tooltip": "Painter",
        }
        """
        data[4] = {
            "uuid": uuid.uuid4(),
            "pid": 4,
            "idx": 4,
            "type": self.TAB_NOTEPAD,
            "data_id": 1,
            "title": "Notepad",
            "tooltip": "Notepad",
        }
        """
        # load notepads from db
        next_idx = 4
        notepads_dict = self.window.core.notepad.import_from_db()
        if notepads_dict is not None:
            for idx in notepads_dict:
                item = notepads_dict[idx]
                data[next_idx] = {
                    "uuid": uuid.uuid4(),
                    "pid": next_idx,
                    "idx": next_idx,
                    "type": self.TAB_NOTEPAD,
                    "data_id": item['data_id'],
                    "title": item['title'],
                    "tooltip": item['title'],
                }
                next_idx += 1
        return data

    def load(self):
        """Load tabs data from config"""
        data = self.window.core.config.get("tabs.data")
        if data is None or len(data) == 0:
            data = self.from_defaults()

        # check for required tabs
        tmp_pid = -1  # tmp PID only for loading
        required = [Tab.TAB_CHAT, Tab.TAB_FILES, Tab.TAB_TOOL_CALENDAR, Tab.TAB_TOOL_PAINTER]
        for type in required:
            found = False
            for pid in data:
                if data[pid]["type"] == type:
                    found = True
                    break
            if not found:
                data[tmp_pid + 1] = {
                    "uuid": str(uuid.uuid4()),
                    "pid": tmp_pid + 1,
                    "idx": tmp_pid + 1,
                    "type": type,
                    "data_id": None,
                    "title": trans(self.titles[type]),
                    "tooltip": trans(self.titles[type]),
                    "custom_name": False,
                }
                tmp_pid += 1

        # sort PIDs by idx
        data = dict(sorted(data.items(), key=lambda item: item[1]["idx"]))
        # regenerate PIDS, enumerate from 0
        n = 0
        for pid in data:
            tab = data[pid]
            tab['pid'] = n
            self.restore(tab)
            n += 1
        self.update()

    def save(self):
        """Save tabs data to config"""
        data = {}
        for pid in self.pids:
            tab = self.pids[pid]
            data[pid] = {
                "uuid": str(tab.uuid),
                "pid": tab.pid,
                "idx": tab.idx,
                "type": tab.type,
                "data_id": tab.data_id,
                "title": tab.title,
                "tooltip": tab.tooltip,
                "custom_name": tab.custom_name,
            }
        self.window.core.config.set("tabs.data", data)
        self.window.core.config.save()

    def update_title(self, idx: int, title: str, tooltip: str = None):
        """
        Update tab title

        :param idx: Tab index
        :param title: Tab title
        :param tooltip: Tab tooltip
        """
        tab = self.get_tab_by_index(idx)
        if tab is None:
            return
        tab.title = title
        tab.tooltip = tooltip
        tab.custom_name = True
        if title is not None:
            self.window.ui.tabs['output'].setTabText(idx, title)
        if tooltip is not None:
            self.window.ui.tabs['output'].setTabToolTip(idx, tooltip)

    def reload_titles(self):
        """Reload default tab titles"""
        counters = {
            self.TAB_CHAT: 1,
            self.TAB_NOTEPAD: 1,
            self.TAB_FILES: 1,
            self.TAB_TOOL_PAINTER: 1,
            self.TAB_TOOL_CALENDAR: 1,
        }
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.custom_name:
                continue  # leave custom names
            tab.title = trans(self.titles[tab.type])
            num_tabs = self.count_by_type(tab.type)
            if num_tabs > 1:
                tab.title += " {}".format(counters[tab.type])
                counters[tab.type] += 1
            self.window.ui.tabs['output'].setTabText(tab.idx, tab.title)
            self.window.ui.tabs['output'].setTabToolTip(tab.idx, tab.title)

    def from_widget(self, widget: QWidget) -> TabBody:
        """
        Prepare tab body from widget

        :param widget: QWidget
        :return: TabBody
        """
        layout = QVBoxLayout()
        layout.addWidget(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = TabBody()
        widget.setLayout(layout)
        return widget

    def from_layout(self, layout: QLayout) -> TabBody:
        """
        Prepare tab body from layout

        :param layout: QLayout
        :return: TabBody
        """
        layout.setContentsMargins(0, 0, 0, 0)
        widget = TabBody()
        widget.setLayout(layout)
        return widget