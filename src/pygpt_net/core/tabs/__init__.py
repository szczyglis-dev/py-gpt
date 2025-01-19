#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.19 02:00:00                  #
# ================================================== #

import uuid
from datetime import datetime
from typing import Optional, Any, Dict

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLayout

from pygpt_net.ui.widget.tabs.body import TabBody
from pygpt_net.utils import trans

from .tab import Tab


class Tabs:

    # number of columns
    NUM_COLS = 2

    def __init__(self, window=None):
        """
        Tabs core

        :param window: Window instance
        """
        self.window = window
        self.last_pid = -1
        self.pids = {}  # pid: Tab data
        self.icons = {
            Tab.TAB_CHAT: ":/icons/chat.svg",
            Tab.TAB_NOTEPAD: ":/icons/paste.svg",
            Tab.TAB_FILES: ":/icons/folder_filled.svg",
            Tab.TAB_TOOL_PAINTER: ":/icons/brush.svg",
            Tab.TAB_TOOL_CALENDAR: ":/icons/calendar.svg",
            Tab.TAB_TOOL: ":/icons/build.svg",
        }
        self.titles = {
            Tab.TAB_CHAT: "output.tab.chat",
            Tab.TAB_NOTEPAD: "output.tab.notepad",
            Tab.TAB_FILES: "output.tab.files",
            Tab.TAB_TOOL_PAINTER: "output.tab.painter",
            Tab.TAB_TOOL_CALENDAR: "output.tab.calendar",
            Tab.TAB_TOOL: "output.tab.tool",
        }

    def get_tab_by_index(
            self,
            idx: int,
            column_idx: int = 0
    ) -> Optional[Tab]:
        """
        Get tab by index

        :param idx: Tab index
        :param column_idx: Column index
        :return: Tab
        """
        tab = self.window.ui.layout.get_tabs_by_idx(column_idx).widget(idx)
        if tab is None:
            return None
        return tab.getOwner()

    def get_tab_by_pid(self, pid: int) -> Optional[Tab]:
        """
        Get tab by PID

        :param pid: PID
        :return: Tab
        """
        if pid in self.pids:
            return self.pids[pid]
        return None

    def get_first_tab_by_type(self, type: int) -> Optional[Tab]:
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

    def get_active_pid(self) -> Optional[int]:
        """
        Get PID by active tab

        :return: PID
        """
        current_column_idx = self.window.controller.ui.tabs.get_current_column_idx()
        tabs = self.window.ui.layout.get_tabs_by_idx(current_column_idx)
        tab = self.get_tab_by_index(tabs.currentIndex(), current_column_idx)
        if tab is None:
            return 0
        return tab.pid

    def add(
            self,
            type: int,
            title: str,
            icon: Optional[str] = None,
            child: Optional[TabBody] = None,
            data_id: Optional[int] = None,
            tool_id: Optional[str] = None
    ) -> Tab:
        """
        Add tab

        :param type: Tab type
        :param title: Tab title
        :param icon: Tab icon
        :param child: Tab child (TabBody)
        :param data_id: Tab data ID
        :param tool_id: Tool ID
        :return: Tab
        """
        self.last_pid += 1  # PID++, start from 0

        tab = Tab()
        tab.uuid = uuid.uuid4()
        tab.pid = self.last_pid
        tab.type = type
        tab.title = title
        tab.icon = icon
        tab.child = child
        tab.data_id = data_id
        tab.tool_id = tool_id

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
        elif type == Tab.TAB_TOOL:
            self.add_tool(tab)

        self.pids[tab.pid] = tab
        return tab

    def append(
            self,
            type: int,
            tool_id: str,
            idx: int,
            column_idx: int = 0
    ) -> Tab:
        """
        Append tab to the right side of the tab with the specified index

        :param type: tab type
        :param tool_id: tool ID
        :param idx: index of the tab to the right of which the new tab will be added
        :param column_idx: index of the column in which the tab will be added
        :return: Tab
        """
        self.last_pid += 1  # PID++, start from 0
        title = ""
        icon = self.icons[type]
        if type == Tab.TAB_CHAT:
            title = trans('output.tab.chat') + " {}".format(self.count_by_type(type) + 1)
        elif type == Tab.TAB_NOTEPAD:
            title = trans('output.tab.notepad') + " {}".format(self.count_by_type(type) + 1)

        tab = Tab()
        tab.uuid = uuid.uuid4()
        tab.pid = self.last_pid
        tab.type = type
        tab.title = title
        tab.icon = icon
        tab.new_idx = idx + 1  # place on right side
        tab.column_idx = column_idx
        tab.tool_id = tool_id

        if type == Tab.TAB_CHAT:
            self.add_chat(tab)
        elif type == Tab.TAB_NOTEPAD:
            self.add_notepad(tab)
        elif type == Tab.TAB_TOOL:
            self.add_tool(tab)

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
        tab.child = None

        if 'tooltip' in data and data['tooltip'] is not None:
            tab.tooltip = data['tooltip']

        if 'custom_name' in data and data['custom_name'] is not None:
            tab.custom_name = data['custom_name']

        if 'column_idx' in data and data['column_idx'] is not None:
            tab.column_idx = data['column_idx']

        if 'tool_id' in data and data['tool_id'] is not None:
            tab.tool_id = data['tool_id']

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
        elif tab.type == Tab.TAB_TOOL:  # custom tools, id 100+
            self.add_tool(tab)

        self.pids[tab.pid] = tab
        self.last_pid = self.get_max_pid()

    def remove_tab_by_idx(
            self,
            idx: int,
            column_idx: int = 0
    ):
        """
        Remove tab by index

        :param idx: Tab index
        :param column_idx: Column index
        """
        tab = self.get_tab_by_index(idx, column_idx)
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
        column_idx = tab.column_idx
        self.window.ui.layout.get_tabs_by_idx(column_idx).removeTab(tab.idx)
        del self.pids[pid]
        self.update()

    def remove_all(self):
        """Remove all tabs"""
        for pid in list(self.pids):
            self.remove(pid)  # delete from PIDs and UI
        self.window.core.ctx.output.clear()  # clear mapping

    def remove_all_by_type(
            self,
            type: int,
            column_idx: int = 0
    ):
        """
        Remove all tabs by type

        :param type: Tab type
        :param column_idx: Column index
        """
        for pid in list(self.pids):
            tab = self.pids[pid]
            if tab.type == type and tab.column_idx == column_idx:
                if type == Tab.TAB_CHAT:
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

    def get_max_data_id_by_type(self, type: int) -> int:
        """
        Get max data ID by type

        :param type: Tab type
        :return: Max data ID
        """
        max = 0
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.type == type and tab.data_id > max:
                max = tab.data_id
        return max

    def get_order_by_idx_and_type(
            self,
            idx: int,
            type: int
    ) -> int:
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

    def get_min_idx_by_type(
            self,
            type: int,
            column_idx: int = 0
    ) -> int:
        """
        Get min index by type

        :param type: Tab type
        :param column_idx: Column index
        :return: Min index
        """
        min = 999999
        for pid in self.pids:
            tab = self.pids[pid]
            if (tab.type == type
                    and tab.column_idx == column_idx
                    and tab.idx < min):
                min = tab.idx
        return min

    def update(self):
        """Update tabs data (pids) from UI (all columns)"""
        for n in range(0, self.NUM_COLS):
            self.update_column(n)

    def update_column(self, column_idx: int):
        """
        Update column data by index

        :param column_idx: Column index
        """
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        for pid in self.pids:
            tab = self.pids[pid]
            if tab.column_idx == column_idx:
                tab.idx = tabs.indexOf(tab.child)
                tab.title = tabs.tabText(tab.idx)
                tab.tooltip = tabs.tabToolTip(tab.idx)
                tab.updated_at = datetime.now()

    def add_chat(self, tab: Tab):
        """
        Add chat tab

        :param tab: Tab instance
        """
        column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        tabs = column.get_tabs()
        tab.parent = column
        tab.child = self.window.core.ctx.container.get(tab)  # tab is already appended here
        if tab.new_idx is not None:
            tab.idx = tabs.insertTab(tab.new_idx, tab.child, tab.title)
        else:
            tab.idx = tabs.addTab(tab.child, tab.title)
        tab.child.setOwner(tab)
        tabs.setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            tabs.setTabToolTip(tab.idx, tab.tooltip)

    def add_notepad(self, tab: Tab):
        """
        Add notepad tab

        :param tab: Tab instance
        """
        idx = None
        column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        tabs = column.get_tabs()
        tab.parent = column
        tab.parent = tabs.get_column()
        if tab.data_id is not None:
            idx = tab.data_id  # restore prev idx
        tab.child, idx, data_id = self.window.controller.notepad.create(idx)
        tab.data_id = data_id  # notepad idx in db, enumerated from 1
        if tab.new_idx is not None:
            tab.idx = tabs.insertTab(tab.new_idx, tab.child, tab.title)
        else:
            tab.idx = tabs.addTab(tab.child, tab.title)
        tab.child.setOwner(tab)
        tabs.setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            tabs.setTabToolTip(tab.idx, tab.tooltip)

    def add_tool_explorer(self, tab: Tab):
        """
        Add explorer tab

        :param tab: Tab instance
        """
        column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        tabs = column.get_tabs()
        tab.parent = column
        tab.child = self.window.ui.chat.output.explorer.setup()
        tab.idx = tabs.addTab(tab.child, tab.title)
        tab.child.setOwner(tab)
        tabs.setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            tabs.setTabToolTip(tab.idx, tab.tooltip)

    def add_tool_painter(self, tab: Tab):
        """
        Add painter tab

        :param tab: Tab instance
        """
        column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        tabs = column.get_tabs()
        tab.parent = column
        tab.child = self.window.ui.chat.output.painter.setup()
        tab.child.append(self.window.ui.painter)
        tab.idx = tabs.addTab(tab.child, tab.title)
        tab.child.setOwner(tab)
        tabs.setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            tabs.setTabToolTip(tab.idx, tab.tooltip)

    def add_tool_calendar(self, tab: Tab):
        """
        Add calendar tab

        :param tab: Tab instance
        """
        column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        tabs = column.get_tabs()
        tab.parent = column
        tab.child = self.window.ui.chat.output.calendar.setup()
        tab.idx = tabs.addTab(tab.child, tab.title)
        tab.child.setOwner(tab)
        tabs.setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            tabs.setTabToolTip(tab.idx, tab.tooltip)

    def add_tool(self, tab: Tab):
        """
        Add custom tool tab

        :param tab: Tab instance
        """
        column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        tabs = column.get_tabs()
        tool = self.window.tools.get(tab.tool_id)
        if tool is None:
            raise Exception("Tool not found: {}".format(tab.tool_id))
        widget = tool.as_tab(tab)
        if widget is None:
            raise Exception("Tool widget not found: {}".format(tab.tool_id))
        tab.icon = tool.tab_icon
        tab.title = trans(tool.tab_title)
        tab.parent = column
        tab.child = self.from_widget(widget)
        tab.idx = tabs.addTab(tab.child, tab.title)
        tab.child.setOwner(tab)
        tabs.setTabIcon(tab.idx, QIcon(tab.icon))
        if tab.tooltip is not None:
            tabs.setTabToolTip(tab.idx, tab.tooltip)

    def move_tab(self, tab: Tab, column_idx: int):
        """
        Move tab to column

        :param tab: Tab instance
        :param column_idx: Column index
        """
        if tab is None:
            return
        if tab.column_idx == column_idx:
            return

        old_column = self.window.ui.layout.get_column_by_idx(tab.column_idx)
        old_tabs = old_column.get_tabs()
        old_tabs.removeTab(tab.idx)
        new_column = self.window.ui.layout.get_column_by_idx(column_idx)
        new_tabs = new_column.get_tabs()
        tab.idx = new_tabs.addTab(tab.child, QIcon(tab.icon), tab.title)
        tab.parent = new_column
        tab.column_idx = column_idx
        self.update()

    def get_first_by_type(self, type: int) -> Optional[Tab]:
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

    def from_defaults(self) -> Dict[int, Any]:
        """
        Prepare default tabs data

        :return: Dict with tabs data
        """
        data = {}
        data[0] = {
            "uuid": uuid.uuid4(),
            "pid": 0,
            "idx": 0,
            "type": Tab.TAB_CHAT,
            "data_id": None,
            "title": "Chat",
            "tooltip": "Chat",
            "column_idx": 0,
        }
        data[1] = {
            "uuid": uuid.uuid4(),
            "pid": 1,
            "idx": 1,
            "type": Tab.TAB_FILES,
            "data_id": None,
            "title": "Files",
            "tooltip": "Files",
            "column_idx": 0,
            "tool_id": "explorer",
        }
        data[2] = {
            "uuid": uuid.uuid4(),
            "pid": 2,
            "idx": 2,
            "type": Tab.TAB_TOOL_CALENDAR,
            "data_id": None,
            "title": "Calendar",
            "tooltip": "Calendar",
            "column_idx": 0,
            "tool_id": "calendar",
        }
        data[3] = {
            "uuid": uuid.uuid4(),
            "pid": 3,
            "idx": 3,
            "type": Tab.TAB_TOOL_PAINTER,
            "data_id": None,
            "title": "Painter",
            "tooltip": "Painter",
            "column_idx": 0,
            "tool_id": "painter",
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
            "column_idx": 0,
            "tool_id": "notepad",
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
                    "type": Tab.TAB_NOTEPAD,
                    "data_id": item['data_id'],
                    "title": item['title'],
                    "tooltip": item['title'],
                    "column_idx": 0,
                    "tool_id": "notepad",
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
                    "column_idx": 0,
                    "tool_id": None,
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
                "column_idx": tab.column_idx,
                "tool_id": tab.tool_id,
            }
        opened_tabs = {}
        for column_idx in range(0, self.NUM_COLS):
            tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
            opened_tabs[column_idx] = tabs.currentIndex()
        self.window.core.config.set("tabs.opened", opened_tabs)
        self.window.core.config.set("tabs.data", data)
        self.window.core.config.save()

    def update_title(
            self,
            idx: int,
            title: str,
            tooltip: Optional[str] = None
    ):
        """
        Update tab title

        :param idx: Tab index
        :param title: Tab title
        :param tooltip: Tab tooltip
        """
        column_idx = self.window.controller.ui.tabs.get_current_column_idx()
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        tab = self.get_tab_by_index(idx, column_idx)
        if tab is None:
            return
        tab.title = title
        tab.tooltip = tooltip
        tab.custom_name = True
        if title is not None:
            tabs.setTabText(idx, title)
        if tooltip is not None:
            tabs.setTabToolTip(idx, tooltip)

    def reload_titles(self):
        """Reload default tab titles"""
        return
        processed = []
        for column_idx in range(0, self.NUM_COLS):
            tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
            counters = {
                Tab.TAB_CHAT: 1,
                Tab.TAB_NOTEPAD: 1,
                Tab.TAB_FILES: 1,
                Tab.TAB_TOOL_PAINTER: 1,
                Tab.TAB_TOOL_CALENDAR: 1,
            }
            for pid in self.pids:
                tab = self.pids[pid]
                if tab.pid in processed:
                    continue
                if tab.custom_name or tab.type == Tab.TAB_TOOL:
                    continue  # leave custom names and tools
                tab.title = trans(self.titles[tab.type])
                num_tabs = self.count_by_type(tab.type)
                if num_tabs > 1:
                    if tab.type in counters:
                        tab.title += " {}".format(counters[tab.type])
                    else:
                        counters[tab.type] = 1
                    counters[tab.type] += 1
                tabs.setTabText(tab.idx, tab.title)
                tabs.setTabToolTip(tab.idx, tab.title)
                processed.append(pid)

    def from_widget(self, widget: QWidget) -> TabBody:
        """
        Prepare tab body from widget

        :param widget: QWidget
        :return: TabBody
        """
        layout = QVBoxLayout()
        layout.addWidget(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        tab_widget = TabBody(self.window)
        tab_widget.append(widget)
        tab_widget.setLayout(layout)
        return tab_widget

    def from_layout(self, layout: QLayout) -> TabBody:
        """
        Prepare tab body from layout

        :param layout: QLayout
        :return: TabBody
        """
        layout.setContentsMargins(0, 0, 0, 0)
        widget = TabBody(self.window)
        widget.setLayout(layout)
        return widget