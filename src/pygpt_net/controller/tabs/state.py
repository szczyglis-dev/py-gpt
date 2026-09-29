#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class TabTarget:
    """Stable address of one concrete output tab."""

    pid: int
    column_idx: int
    idx: int


@dataclass
class TabState:
    """Single source of truth for output-tab selection/focus state.

    Qt widgets still own their visual currentIndex, while this object owns the
    logical active column and the last selected tab identity per column. Every
    controller operation updates this state from an explicit (column, index,
    pid) tuple instead of inferring a target from keyboard focus later.
    """

    active_column: int = 0
    current_by_column: Dict[int, int] = field(default_factory=lambda: {0: 0, 1: 0})
    pid_by_column: Dict[int, int] = field(default_factory=dict)
    initialized: bool = False
    loading_widgets: bool = False
    locked: bool = False
    pending_focus_column: Optional[int] = None


    def lock(self) -> None:
        self.locked = True

    def unlock(self) -> None:
        self.locked = False

    def is_locked(self) -> bool:
        return self.locked

    def mark_initialized(self) -> None:
        self.initialized = True

    def mark_uninitialized(self) -> None:
        self.initialized = False

    def is_initialized(self) -> bool:
        return self.initialized

    def begin_widget_loading(self) -> None:
        self.loading_widgets = True

    def end_widget_loading(self) -> None:
        self.loading_widgets = False

    def is_widget_loading(self) -> bool:
        return self.loading_widgets

    def set_active_column(self, column_idx: int) -> None:
        column_idx = int(column_idx)
        self.active_column = column_idx
        self.current_by_column.setdefault(column_idx, 0)

    def get_active_column(self) -> int:
        return int(self.active_column)

    def clear_column_pid(self, column_idx: int) -> None:
        self.pid_by_column.pop(int(column_idx), None)

    def set_pending_focus_column(self, column_idx: Optional[int]) -> None:
        self.pending_focus_column = None if column_idx is None else int(column_idx)

    def get_pending_focus_column(self) -> Optional[int]:
        return self.pending_focus_column

    def clear_pending_focus_column(self) -> None:
        self.pending_focus_column = None

    def activate(self, column_idx: int, idx: int, pid: Optional[int] = None) -> None:
        column_idx = int(column_idx)
        idx = int(idx)
        self.active_column = column_idx
        self.current_by_column[column_idx] = idx
        if pid is None:
            self.pid_by_column.pop(column_idx, None)
        else:
            self.pid_by_column[column_idx] = int(pid)

    def remember(self, column_idx: int, idx: int, pid: Optional[int] = None) -> None:
        """Remember a column selection without changing the active column."""
        column_idx = int(column_idx)
        self.current_by_column[column_idx] = int(idx)
        if pid is None:
            self.pid_by_column.pop(column_idx, None)
        else:
            self.pid_by_column[column_idx] = int(pid)

    def current_idx(self, column_idx: Optional[int] = None) -> int:
        if column_idx is None:
            column_idx = self.active_column
        return int(self.current_by_column.get(int(column_idx), 0))

    def current_pid(self, column_idx: Optional[int] = None) -> Optional[int]:
        if column_idx is None:
            column_idx = self.active_column
        return self.pid_by_column.get(int(column_idx))

    def target(self, column_idx: Optional[int] = None) -> Optional[TabTarget]:
        if column_idx is None:
            column_idx = self.active_column
        column_idx = int(column_idx)
        pid = self.pid_by_column.get(column_idx)
        if pid is None:
            return None
        return TabTarget(pid=pid, column_idx=column_idx, idx=self.current_idx(column_idx))

    def reset(self) -> None:
        self.active_column = 0
        self.current_by_column = {0: 0, 1: 0}
        self.pid_by_column.clear()
        self.pending_focus_column = None
        self.locked = False

    def drop_pid(self, pid: int) -> None:
        for column_idx, selected_pid in list(self.pid_by_column.items()):
            if selected_pid == pid:
                self.pid_by_column.pop(column_idx, None)
