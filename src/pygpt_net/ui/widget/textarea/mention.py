#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 23:00:00                  #
# ================================================== #

from dataclasses import dataclass
from typing import Iterable, Optional

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)

from pygpt_net.core.text.mentions import KIND_ATTACHMENT, KIND_FILE_CONTEXT
from pygpt_net.utils import trans


@dataclass(frozen=True, slots=True)
class MentionEntry:
    kind: str
    label: str
    value: str
    is_dir: bool = False


class MentionPopup(QFrame):
    """Small non-activating picker shown above an active ``@`` trigger."""

    selected = Signal(object)

    ROLE_ENTRY = Qt.UserRole + 41
    ROLE_HEADER = Qt.UserRole + 42
    MAX_VISIBLE_ROWS = 9
    MAX_RESULTS = 250
    WIDTH = 430

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint)
        self.setProperty("class", "mention-popup")
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.NoFocus)

        self.list = QListWidget(self)
        self.list.setProperty("class", "mention-popup-list")
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.ElideMiddle)
        self.list.itemClicked.connect(self._activate_item)
        self.list.itemActivated.connect(self._activate_item)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.list)

        self._entries: list[MentionEntry] = []
        self._query = ""
        self.hide()

    def set_entries(self, entries: Iterable[MentionEntry]):
        self._entries = list(entries or [])
        self._query = ""
        self.apply_filter("")

    def apply_filter(self, query: str) -> bool:
        self._query = str(query or "").strip().casefold()
        matches = []
        for entry in self._entries:
            haystack = f"{entry.label}\n{entry.value}".casefold()
            if not self._query or self._query in haystack:
                matches.append(entry)

        self.list.clear()
        attachments = [e for e in matches if e.kind == KIND_ATTACHMENT]
        files = [e for e in matches if e.kind == KIND_FILE_CONTEXT]

        attachments.sort(key=lambda e: e.label.casefold())
        files.sort(key=lambda e: (not e.is_dir, e.label.casefold()))

        # Keep the widget light even for very large project data trees. Filtering
        # still runs against the full entry set, so typing narrows into items
        # that were not present in the initial visible slice.
        visible = []
        visible.extend(attachments)
        visible.extend(files)
        visible = visible[:self.MAX_RESULTS]
        attachments = [e for e in visible if e.kind == KIND_ATTACHMENT]
        files = [e for e in visible if e.kind == KIND_FILE_CONTEXT]

        if attachments:
            self._add_header(trans("attachments.tab"))
            for entry in attachments:
                self._add_entry(entry)
        if files:
            self._add_header(trans("output.tab.files"))
            for entry in files:
                self._add_entry(entry)

        self._select_first()
        self._resize_for_items()
        if self.list.count() == 0:
            self.hide()
            return False
        return True

    def _add_header(self, text: str):
        item = QListWidgetItem(text)
        item.setData(self.ROLE_HEADER, True)
        item.setFlags(Qt.NoItemFlags)
        font = QFont(item.font())
        font.setBold(True)
        item.setFont(font)
        self.list.addItem(item)

    def _add_entry(self, entry: MentionEntry):
        label = entry.label
        if entry.kind == KIND_FILE_CONTEXT and entry.is_dir and not label.endswith("/"):
            label += "/"
        item = QListWidgetItem(label)
        item.setData(self.ROLE_ENTRY, entry)
        item.setToolTip(entry.value)
        self.list.addItem(item)

    def _select_first(self):
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item is not None and item.data(self.ROLE_ENTRY) is not None:
                self.list.setCurrentRow(row)
                return

    def _resize_for_items(self):
        rows = min(max(self.list.count(), 1), self.MAX_VISIBLE_ROWS)
        row_h = self.list.sizeHintForRow(0)
        if row_h <= 0:
            row_h = 28
        height = min(280, max(54, rows * row_h + 4))
        self.resize(self.WIDTH, height)

    def _activate_item(self, item: Optional[QListWidgetItem]):
        if item is None:
            return
        entry = item.data(self.ROLE_ENTRY)
        if entry is None:
            return
        self.hide()
        self.selected.emit(entry)

    def current_entry(self) -> Optional[MentionEntry]:
        item = self.list.currentItem()
        if item is None:
            return None
        return item.data(self.ROLE_ENTRY)

    def choose_current(self) -> bool:
        entry = self.current_entry()
        if entry is None:
            return False
        self.hide()
        self.selected.emit(entry)
        return True

    def move_selection(self, delta: int):
        count = self.list.count()
        if count <= 0:
            return
        row = self.list.currentRow()
        if row < 0:
            row = 0 if delta >= 0 else count - 1
        for _ in range(count):
            row = (row + delta) % count
            item = self.list.item(row)
            if item is not None and item.data(self.ROLE_ENTRY) is not None:
                self.list.setCurrentRow(row)
                self.list.scrollToItem(item, QAbstractItemView.EnsureVisible)
                return

    def show_above(self, anchor_global: QPoint):
        if self.list.count() <= 0:
            self.hide()
            return

        self._resize_for_items()
        screen = QApplication.screenAt(anchor_global)
        geometry = screen.availableGeometry() if screen is not None else QApplication.primaryScreen().availableGeometry()

        x = anchor_global.x()
        y = anchor_global.y() - self.height() - 6
        x = max(geometry.left() + 4, min(x, geometry.right() - self.width() - 4))
        if y < geometry.top() + 4:
            y = anchor_global.y() + 22
        y = max(geometry.top() + 4, min(y, geometry.bottom() - self.height() - 4))

        self.move(x, y)
        self.show()
        self.raise_()
