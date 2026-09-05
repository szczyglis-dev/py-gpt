#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 04:00:00                  #
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
        # [meta_id -> pid] render target pinned for the lifetime of the current
        # request/tool chain. This keeps streaming bound to the chat tab where
        # generation started even if focus moves to another split-screen column.
        self.render_pids: Dict[int, int] = {}
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
        if force:
            self.render_pids.clear()

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
        in_second_column = False
        if tab is None:
            return None

        # 1) check current column
        col_idx = tab.column_idx
        col_map = self.mapping.get(col_idx, {})
        if not isinstance(col_map, dict):
            return None

        candidates = [pid for pid, meta_id in col_map.items() if meta_id == meta.id]
        for pid in candidates:
            if pid == active_pid:  # prefer active PID
                return pid
        pid = candidates[-1] if candidates else None

        # 2) check if mapped in other columns
        if pid is None:
            for idx, other_col_map in self.mapping.items():
                if idx == col_idx:
                    continue
                for other_pid, meta_id in other_col_map.items():
                    if meta_id == meta.id:
                        in_second_column = True
                        pid = other_pid
                        break
                if pid is not None:
                    break

        if in_second_column and not self.window.controller.chat.input.generating:
            return None # allow remapping only when not generating

        return pid  # return last found PID

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

    def pin_render_pid(
            self,
            meta: Optional[CtxMeta],
            pid: Optional[int] = None,
            force: bool = False,
    ) -> Optional[int]:
        """
        Pin a context meta to a concrete chat-tab PID for rendering.

        Once pinned, renderer lookups no longer follow the currently focused
        split-screen column. This is required for streaming responses: clicking
        a tool (for example Code Interpreter) in the other column must not move
        the in-flight response to another output widget.

        Resolution deliberately does not depend on the current ``generating``
        flag. If focus is on a non-chat tool, an already mapped chat tab for the
        meta is used. This also keeps later tool/agent response segments on the
        original chat column.

        :param meta: Context meta
        :param pid: Explicit chat tab PID; auto-resolve if None
        :param force: Replace an existing pin
        :return: Pinned PID or None
        """
        self.init()
        if meta is None or getattr(meta, "id", None) is None:
            return None

        meta_id = meta.id
        if not force:
            pinned = self.render_pids.get(meta_id)
            if pinned is not None:
                tab = self.window.core.tabs.get_tab_by_pid(pinned)
                if tab is not None and tab.type == Tab.TAB_CHAT:
                    return pinned
                self.render_pids.pop(meta_id, None)

        tabs = self.window.core.tabs
        if pid is None:
            # Prefer the active tab only when it is a chat already displaying
            # this meta. This is the normal top-level user-send path.
            active_pid = tabs.get_active_pid()
            active_tab = tabs.get_tab_by_pid(active_pid)
            if active_tab is not None and active_tab.type == Tab.TAB_CHAT:
                active_meta_id = self.mapping.get(active_tab.column_idx, {}).get(active_pid)
                if active_meta_id == meta_id or getattr(active_tab, "data_id", None) == meta_id:
                    pid = active_pid

            # If focus moved to a tool/non-chat tab, resolve the already mapped
            # chat target without using the active-column preference from
            # get_mapped(). Prefer the most recently used matching PID when the
            # same context is visible in more than one chat tab.
            if pid is None:
                candidates = []
                for col_map in self.mapping.values():
                    for mapped_pid, mapped_meta_id in col_map.items():
                        if mapped_meta_id != meta_id:
                            continue
                        tab = tabs.get_tab_by_pid(mapped_pid)
                        if tab is not None and tab.type == Tab.TAB_CHAT:
                            candidates.append(mapped_pid)
                if self.last_pid in candidates:
                    pid = self.last_pid
                elif candidates:
                    pid = candidates[-1]

            # New/unmapped context: only create the mapping from a real active
            # chat tab. Never interpret store()'s legacy 0 sentinel as PID 0
            # while a tool tab has focus.
            if pid is None:
                if active_tab is None or active_tab.type != Tab.TAB_CHAT:
                    return None
                pid = self.store(meta)

        tab = tabs.get_tab_by_pid(pid) if pid is not None else None
        if tab is None or tab.type != Tab.TAB_CHAT:
            return None

        self.render_pids[meta_id] = pid
        return pid

    def unpin_render_pid(self, meta: Optional[CtxMeta] = None, pid: Optional[int] = None):
        """
        Remove a pinned render target by meta or PID.

        :param meta: Context meta
        :param pid: Chat tab PID
        """
        if meta is not None and getattr(meta, "id", None) is not None:
            self.render_pids.pop(meta.id, None)
        if pid is not None:
            for meta_id, pinned_pid in list(self.render_pids.items()):
                if pinned_pid == pid:
                    self.render_pids.pop(meta_id, None)

    def get_pid(self, meta: Optional[CtxMeta] = None) -> Optional[int]:
        """
        Get PID by meta (pinned render target first, then active mapping).

        :param meta: Meta
        :return: PID or None
        """
        self.init()
        if meta is None:
            return None

        meta_id = getattr(meta, "id", None)
        if meta_id is not None:
            pinned = self.render_pids.get(meta_id)
            if pinned is not None:
                tab = self.window.core.tabs.get_tab_by_pid(pinned)
                if tab is not None and tab.type == Tab.TAB_CHAT:
                    return pinned
                # The pinned tab was closed/removed. Drop the stale pin and
                # fall back to normal mapping resolution.
                self.render_pids.pop(meta_id, None)

        tabs = self.window.core.tabs
        active_pid = tabs.get_active_pid()
        mapped_pid = self.get_mapped(meta)
        if mapped_pid == active_pid:
            pid = active_pid
        else:
            if mapped_pid is None:
                pid = self.store(meta)
            else:
                pid = mapped_pid
        return pid

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
        self.unpin_render_pid(pid=pid)
        if pid == self.last_pid:
            self.last_pid = 0

    def clear(self):
        """Clear mapping"""
        self.mapping.clear()
        self.last_pids.clear()
        self.render_pids.clear()
        self.last_pid = 0
        self.initialized = False
