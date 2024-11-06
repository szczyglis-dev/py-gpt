#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.core.tabs.tab import Tab

class Output:
    def __init__(self, window=None):
        """
        Context output mapping
        """
        self.window = window
        self.mapping = {}  # pid => meta.id
        self.last_pids = {}  # meta.id => pid
        self.last_pid = 0 # last used PID

    def store(self, meta: CtxMeta) -> int:
        """
        Store meta in mapping

        :param meta: Meta
        :return: PID
        """
        pid = self.window.core.tabs.get_active_pid()
        # check if allowed tab
        tab = self.window.core.tabs.get_tab_by_pid(pid)
        if tab is None or tab.type != Tab.TAB_CHAT:
            return 0
        self.mapping[pid] = meta.id
        self.last_pids[meta.id] = pid
        self.last_pid = pid
        tab = self.window.core.tabs.get_tab_by_pid(pid)
        if tab is not None:
            tab.data_id = meta.id  # store meta id in tab data
        return pid

    def meta_id_in_tab(self, meta_id: int) -> bool:
        """
        Check if meta id is in tab

        :param meta_id: Meta ID
        :return: bool
        """
        for pid, mid in self.mapping.items():
            if mid == meta_id:
                return True
        return False

    def is_mapped(self, meta: CtxMeta) -> bool:
        """
        Check if meta is mapped

        :param meta: Meta
        :return: bool
        """
        return meta.id in self.mapping.values()

    def get_meta(self, pid: int) -> CtxMeta or None:
        """
        Get meta by PID

        :param pid: PID
        :return: Meta or None
        """
        if pid in self.mapping:
            return self.mapping[pid]
        return

    def get_mapped(self, meta: CtxMeta) -> int or None:
        """
        Get PID by meta

        :param meta: Meta
        :return: PID or None
        """
        all = []
        pid = None
        active_pid = self.window.core.tabs.get_active_pid()
        for pid, meta_id in self.mapping.items():
            if meta_id == meta.id:
                all.append(pid)
        for pid in all:
            if pid == active_pid:  # at first check if active
                return pid
        return pid

    def get_mapped_last(self, meta: CtxMeta) -> int or None:
        """
        Get last PID by meta

        :param meta: Meta
        :return: PID or None
        """
        active_pid = self.window.core.tabs.get_active_pid()
        if self.mapping[active_pid] == meta.id:
            return active_pid  # return active PID at first
        if meta.id in self.last_pids:
            return self.last_pids[meta.id]
        return

    def prepare(self, meta: CtxMeta):
        """
        Clear mapping

        :param meta: meta to prepare
        """
        active_pid = self.window.core.tabs.get_active_pid()
        if active_pid in self.mapping:
            del self.mapping[active_pid]  # remove from mapping

    def clear(self):
        """
        Clear mapping
        """
        self.mapping = {}
        self.last_pids = {}
        self.last_pid = 0

    def is_empty(self) -> bool:
        """
        Check if mapping is empty

        :return: bool
        """
        active_pid = self.window.core.tabs.get_active_pid()
        if active_pid in self.mapping:
            return False
        return True

    def get_pid(self, meta: CtxMeta = None) -> int:
        """
        Get PID by meta

        :param meta: Meta
        :return: PID
        """
        if meta is None:
            return self.window.core.tabs.get_active_pid()
        if self.is_mapped(meta):
            if self.window.core.tabs.get_active_pid() != self.get_mapped(meta):  # if loaded in another tab
                return self.store(meta)  # update to current
            return self.get_mapped_last(meta)
        else:
            return self.store(meta)

    def get_current(self, meta: CtxMeta = None):
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

    def get_current_plain(self, meta: CtxMeta = None):
        """
        Get current output plain node by meta

        :param meta: Meta
        :return: Node
        """
        pid = self.get_pid(meta)
        if pid in self.window.ui.nodes['output_plain']:
            return self.window.ui.nodes['output_plain'][pid]
        else:
            return self.window.ui.nodes['output_plain'][0]

    def get_by_pid(self, pid = None):
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

    def get_by_pid_plain(self, pid = None):
        """
        Get output plain node by PID

        :param pid: PID
        :return: Node widget
        """
        if pid in self.window.ui.nodes['output_plain']:
            return self.window.ui.nodes['output_plain'][pid]
        else:
            return self.window.ui.nodes['output_plain'][0]

    def get_all(self) -> list:
        """
        Get all output nodes

        :return: List of nodes
        """
        nodes = []
        for node in self.window.ui.nodes['output'].values():
            nodes.append(node)
        return nodes

    def get_all_plain(self) -> list:
        """
        Get all output plain nodes

        :return: List of nodes
        """
        nodes = []
        for node in self.window.ui.nodes['output_plain'].values():
            nodes.append(node)
        return nodes