#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.16 22:00:00                  #
# ================================================== #

from typing import Optional, List, Dict

from pygpt_net.item.ctx import CtxMeta
from pygpt_net.core.tabs.tab import Tab


class Output:

    def __init__(self, window=None):
        """
        Context output mapping

        :param window: Window
        """
        self.window = window
        # [column_idx -> {pid -> meta_id}]
        self.mapping: Dict[int, Dict[int, int]] = {}
        # [column_idx -> {meta_id -> pid}] (last used PID for meta)
        self.last_pids: Dict[int, Dict[int, int]] = {}
        self.last_pid: int = 0  # last used PID
        self.initialized: bool = False

    def init(self, force: bool = False):
        """
        Initialize mappings

        :param force: Force reinitialize
        """
        if self.initialized and not force:
            return

        self.mapping.clear()
        self.last_pids.clear()

        tabs = getattr(self.window, "core", None)
        tabs = getattr(tabs, "tabs", None)
        num_cols = getattr(tabs, "NUM_COLS", 0) if tabs is not None else 0

        for n in range(num_cols):
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

        tabs = self.window.core.tabs
        pid = tabs.get_active_pid()
        tab = tabs.get_tab_by_pid(pid)
        if tab is None or tab.type != Tab.TAB_CHAT:
            return 0

        col_idx = tab.column_idx

        col_map = self.mapping.get(col_idx)
        if col_map is None or not isinstance(col_map, dict):
            col_map = self.mapping[col_idx] = {}
        last_map = self.last_pids.get(col_idx)
        if last_map is None:
            last_map = self.last_pids[col_idx] = {}

        col_map[pid] = meta.id
        last_map[meta.id] = pid
        self.last_pid = pid

        tab.data_id = meta.id
        return pid

    def is_mapped(self, meta: CtxMeta) -> bool:
        """
        Check if meta is mapped anywhere

        :param meta: Meta
        :return: True if mapped, False otherwise
        """
        self.init()

        # quick check for the active tab
        tabs = self.window.core.tabs
        active_pid = tabs.get_active_pid()
        tab = tabs.get_tab_by_pid(active_pid)
        if tab is not None:
            col_map = self.mapping.get(tab.column_idx, {})
            # check if meta.id is in the current column mapping
            for mid in col_map.values():
                if mid == meta.id:
                    return True

        # fallback
        for col_idx, col_map in self.mapping.items():
            if tab is not None and col_idx == tab.column_idx:
                continue
            for mid in col_map.values():
                if mid == meta.id:
                    return True
        return False

    def get_meta(self, pid: int) -> Optional[int]:
        """
        Get meta by PID

        :param pid: PID
        :return: meta ID or None
        """
        self.init()

        tabs = self.window.core.tabs
        tab = tabs.get_tab_by_pid(pid)
        if tab is not None:
            return self.mapping.get(tab.column_idx, {}).get(pid)

        # fallback
        for col_map in self.mapping.values():
            if pid in col_map:
                return col_map[pid]
        return None

    def prepare_meta(self, tab: Tab) -> Optional[int]:
        """
        Get meta ID by PID (and store it if not exists)

        :param tab: Tab
        :return: Meta ID or None
        """
        self.init()

        pid = tab.pid
        col_idx = tab.column_idx

        col_map = self.mapping.get(col_idx)
        if col_map is None:
            col_map = self.mapping[col_idx] = {}

        if pid in col_map:
            return col_map[pid]

        meta_id = getattr(tab, "data_id", None)
        if meta_id is not None:
            col_map[pid] = meta_id
            self.last_pids.setdefault(col_idx, {})[meta_id] = pid
            self.last_pid = pid
        return meta_id

    def get_mapped(self, meta: CtxMeta) -> Optional[int]:
        """
        Get PID by meta for the current column (prefer active PID)

        :param meta: Meta
        :return: PID or None
        """
        self.init()

        tabs = self.window.core.tabs
        active_pid = tabs.get_active_pid()
        tab = tabs.get_tab_by_pid(active_pid)
        if tab is None:
            return None
        col_idx = tab.column_idx
        col_map = self.mapping.get(col_idx, {})
        if not isinstance(col_map, dict):
            return None

        candidates = [pid for pid, meta_id in col_map.items() if meta_id == meta.id]
        for pid in candidates:
            if pid == active_pid:  # prefer active PID
                return pid
        return candidates[-1] if candidates else None  # return last found PID

    def is_empty(self) -> bool:
        """
        Check if mapping is empty for the active PID across columns

        :return: True if empty, False otherwise
        """
        self.init()

        tabs = self.window.core.tabs
        active_pid = tabs.get_active_pid()
        for col_map in self.mapping.values():
            if active_pid in col_map:
                return False
        return True

    def get_pid(self, meta: Optional[CtxMeta] = None) -> Optional[int]:
        """
        Get PID by meta (prefer active PID)

        :param meta: Meta
        :return: PID or None
        """
        self.init()
        if meta is None:
            return None

        tabs = self.window.core.tabs
        active_pid = tabs.get_active_pid()
        mapped_pid = self.get_mapped(meta)
        if mapped_pid == active_pid:
            return active_pid
        return self.store(meta)

    def clear(self):
        """Clear mapping"""
        self.mapping.clear()
        self.last_pids.clear()
        self.last_pid = 0
        self.initialized = False

    def get_current(self, meta: Optional[CtxMeta] = None):
        """
        Get current output node by meta

        :param meta: Meta
        :return: Node
        """
        pid = self.get_pid(meta)
        nodes = self.window.ui.nodes['output']
        if pid is not None:
            node = nodes.get(pid)
            if node is not None:
                return node
        # fallback
        return next(iter(nodes.values()), None)

    def get_current_plain(self, meta: Optional[CtxMeta] = None):
        """
        Get current output plain node by meta

        :param meta: Meta
        :return: Node
        """
        pid = self.get_pid(meta)
        nodes = self.window.ui.nodes['output_plain']
        if pid is not None:
            node = nodes.get(pid)
            if node is not None:
                return node
        return next(iter(nodes.values()), None)

    def get_by_pid(self, pid: Optional[int] = None):
        """
        Get output node by PID

        :param pid: PID
        :return: Node widget
        """
        nodes = self.window.ui.nodes['output']
        if pid is not None:
            node = nodes.get(pid)
            if node is not None:
                return node
        return next(iter(nodes.values()), None)

    def get_by_pid_plain(self, pid: Optional[int] = None):
        """
        Get output plain node by PID

        :param pid: PID
        :return: Node widget
        """
        nodes = self.window.ui.nodes['output_plain']
        if pid is not None:
            node = nodes.get(pid)
            if node is not None:
                return node
        return next(iter(nodes.values()), None)

    def get_all(self) -> List:
        """
        Get all output nodes

        :return: List of nodes
        """
        return list(self.window.ui.nodes['output'].values())

    def get_all_plain(self) -> List:
        """
        Get all output plain nodes

        :return: List of nodes
        """
        return list(self.window.ui.nodes['output_plain'].values())

    def remove_pid(self, pid: int):
        """
        Remove PID from mapping

        :param pid: PID
        """
        self.init()
        for col_idx in self.mapping:
            if pid in self.mapping[col_idx]:
                del self.mapping[col_idx][pid]
                break
        if pid in self.last_pids:
            del self.last_pids[pid]
        if pid == self.last_pid:
            self.last_pid = 0