#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Optional, List

from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.core.tabs.tab import Tab

class Output:
    def __init__(self, window=None):
        """
        Context output mapping

        :param window: Window
        """
        self.window = window
        self.mapping = {}  # [column_idx => [pid => meta.id]]
        self.last_pids = {}  # meta.id => pid
        self.last_pid = 0 # last used PID
        self.initialized = False

    def init(self, force: bool = False):
        """
        Initialize mappings

        :param force: Force reinitialize
        """
        if self.initialized and not force:
            return
        self.clear()
        for n in range(0, self.window.core.tabs.NUM_COLS):
            self.mapping[n] = {}
            self.last_pids[n] = {}
        self.initialized = True

    def store(self, meta: CtxMeta) -> int:
        """
        Store meta in mapping

        :param meta: Meta
        :return: PID
        """
        self.init()
        pid = self.window.core.tabs.get_active_pid()
        tab = self.window.core.tabs.get_tab_by_pid(pid)
        if tab is None or tab.type != Tab.TAB_CHAT:
            return 0
        col_idx = tab.column_idx
        self.mapping[col_idx][pid] = meta.id
        self.last_pids[col_idx][meta.id] = pid
        self.last_pid = pid
        tab = self.window.core.tabs.get_tab_by_pid(pid)
        if tab is not None:
            tab.data_id = meta.id  # store meta id in tab data
        return pid

    def is_mapped(self, meta: CtxMeta) -> bool:
        """
        Check if meta is mapped

        :param meta: Meta
        :return: bool
        """
        self.init()
        for col_idx in self.mapping:
            if meta.id in self.mapping[col_idx].values():
                return True
        return False

    def get_meta(self, pid: int) -> Optional[int]:
        """
        Get meta by PID

        :param pid: PID
        :return: meta ID or None
        """
        self.init()
        for col_idx in self.mapping:
            if pid in self.mapping[col_idx]:
                return self.mapping[col_idx][pid]
        return

    def prepare_meta(self, tab: Tab) -> Optional[int]:
        """
        Get meta ID by PID

        :param tab: Tab
        :return: Meta ID or None
        """
        self.init()
        pid = tab.pid
        col_idx = tab.column_idx
        meta_id = None
        if pid in self.mapping[col_idx]:
            return self.mapping[col_idx][pid]
        if meta_id is None:
            meta_id = tab.data_id
            if meta_id is not None:
                self.mapping[col_idx][pid] = meta_id
                self.last_pids[col_idx][meta_id] = pid
                self.last_pid = pid
        return meta_id

    def get_mapped(self, meta: CtxMeta) -> Optional[int]:
        """
        Get PID by meta

        :param meta: Meta
        :return: PID or None
        """
        self.init()
        all = []
        pid = None
        active_pid = self.window.core.tabs.get_active_pid()
        tab = self.window.core.tabs.get_tab_by_pid(active_pid)
        if tab is None:
            return None
        col_idx = tab.column_idx
        for pid, meta_id in self.mapping[col_idx].items():
            if meta_id == meta.id:
                all.append(pid)
        for pid in all:
            if pid == active_pid:  # at first check for current tab
                return pid
        return pid

    def is_empty(self) -> bool:
        """
        Check if mapping is empty

        :return: bool
        """
        self.init()
        active_pid = self.window.core.tabs.get_active_pid()
        for col_idx in list(self.mapping.keys()):
            if active_pid in self.mapping[col_idx]:
                return False
        return True

    def get_pid(self, meta: Optional[CtxMeta] = None) -> Optional[int]:
        """
        Get PID by meta

        :param meta: Meta
        :return: PID
        """
        self.init()
        active_pid = self.window.core.tabs.get_active_pid()
        if meta is None:
            return None
        if self.is_mapped(meta):
            if active_pid == self.get_mapped(meta):  # if loaded in current tab
                return active_pid  # return current
        return self.store(meta)

    def clear(self):
        """
        Clear mapping
        """
        self.mapping = {}
        self.last_pids = {}
        self.last_pid = 0
        self.initialized = False

    def get_current(self, meta: Optional[CtxMeta] = None):
        """
        Get current output node by meta

        :param meta: Meta
        :return: Node
        """
        pid = self.get_pid(meta)
        if pid in self.window.ui.nodes['output']:
            return self.window.ui.nodes['output'][pid]
        else:
            for pid in self.window.ui.nodes['output']:
                return self.window.ui.nodes['output'][pid]  # get first available

    def get_current_plain(self, meta: Optional[CtxMeta] = None):
        """
        Get current output plain node by meta

        :param meta: Meta
        :return: Node
        """
        pid = self.get_pid(meta)
        if pid in self.window.ui.nodes['output_plain']:
            return self.window.ui.nodes['output_plain'][pid]
        else:
            for pid in self.window.ui.nodes['output_plain']:
                return self.window.ui.nodes['output_plain'][pid]

    def get_by_pid(self, pid: Optional[int] = None):
        """
        Get output node by PID

        :param pid: PID
        :return: Node widget
        """
        if pid in self.window.ui.nodes['output']:
            return self.window.ui.nodes['output'][pid]
        else:
            for pid in self.window.ui.nodes['output']:
                return self.window.ui.nodes['output'][pid]  # get first available

    def get_by_pid_plain(self, pid: Optional[int] = None):
        """
        Get output plain node by PID

        :param pid: PID
        :return: Node widget
        """
        if pid in self.window.ui.nodes['output_plain']:
            return self.window.ui.nodes['output_plain'][pid]
        else:
            for pid in self.window.ui.nodes['output_plain']:
                return self.window.ui.nodes['output_plain'][pid]

    def get_all(self) -> List:
        """
        Get all output nodes

        :return: List of nodes
        """
        nodes = []
        for node in self.window.ui.nodes['output'].values():
            nodes.append(node)
        return nodes

    def get_all_plain(self) -> List:
        """
        Get all output plain nodes

        :return: List of nodes
        """
        nodes = []
        for node in self.window.ui.nodes['output_plain'].values():
            nodes.append(node)
        return nodes