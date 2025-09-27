#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 16:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox
from PySide6.QtGui import QFontMetrics, QStandardItem, QStandardItemModel  # keep existing imports, extend with items

from pygpt_net.utils import trans

class SeparatorComboBox(QComboBox):
    """A combo box that supports adding separator items and prevents selecting them."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Custom role used to mark separator rows without interfering with existing UserRole data
        self._SEP_ROLE = Qt.UserRole + 1000
        # Internal guard to avoid recursive index changes
        self._block_guard = False

    def addSeparator(self, text):
        """
        Adds a separator item to the combo box that cannot be selected.
        This keeps separators visible but disabled/unselectable.

        :param text: The text to display for the separator.
        """
        model = self.model()
        if isinstance(model, QStandardItemModel):
            item = QStandardItem(text)
            # Disable and make the row unselectable
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
            # Mark explicitly as separator using custom role
            item.setData(True, self._SEP_ROLE)
            model.appendRow(item)
        else:
            # Fallback: keep previous behavior and additionally tag item with custom role
            index = self.count()
            self.addItem(text)
            try:
                role = Qt.UserRole - 1
                self.setItemData(index, 0, role)  # legacy approach used sometimes to indicate non-enabled
            except Exception:
                pass
            # Tag as separator via custom role for later checks
            self.setItemData(index, True, self._SEP_ROLE)

    def is_separator(self, index: int) -> bool:
        """Returns True if item at index is a separator."""
        if index < 0 or index >= self.count():
            return False
        try:
            if self.itemData(index, self._SEP_ROLE):
                return True
        except Exception:
            pass
        # Fallback: check flags (works with item models)
        try:
            idx = self.model().index(index, self.modelColumn(), self.rootModelIndex())
            flags = self.model().flags(idx)
            if not (flags & Qt.ItemIsEnabled) or not (flags & Qt.ItemIsSelectable):
                return True
        except Exception:
            pass
        return False

    def first_valid_index(self) -> int:
        """Returns the first non-separator index, or -1 if none."""
        for i in range(self.count()):
            if not self.is_separator(i):
                return i
        return -1

    def _sanitize_index(self, index: int) -> int:
        """Returns a corrected non-separator index, or -1 if none available."""
        if index is None:
            index = -1
        if index < 0 or index >= self.count():
            return self.first_valid_index()
        if self.is_separator(index):
            # Prefer the next valid item; if none, scan backwards; else -1
            for i in range(index + 1, self.count()):
                if not self.is_separator(i):
                    return i
            for i in range(index - 1, -1, -1):
                if not self.is_separator(i):
                    return i
            return -1
        return index

    def ensure_valid_current(self) -> int:
        """
        Ensures the current index is not a separator.
        Returns the final valid index (or -1) after correction.
        """
        current = super().currentIndex()
        corrected = self._sanitize_index(current)
        if corrected != current:
            try:
                self._block_guard = True
                super().setCurrentIndex(corrected if corrected != -1 else -1)
            finally:
                self._block_guard = False
        return corrected

    def setCurrentIndex(self, index: int) -> None:
        """
        Prevent setting the current index to a separator from any caller.
        """
        if self._block_guard:
            # When guarded, pass through without checks to avoid recursion
            return super().setCurrentIndex(index)
        corrected = self._sanitize_index(index)
        try:
            self._block_guard = True
            super().setCurrentIndex(corrected if corrected != -1 else -1)
        finally:
            self._block_guard = False


class NoScrollCombo(SeparatorComboBox):
    """A combo box that disables mouse wheel scrolling."""

    def __init__(self, parent=None):
        super(NoScrollCombo, self).__init__(parent)

    def wheelEvent(self, event):
        event.ignore()  # disable mouse wheel

    def showPopup(self):
        max_width = 0
        font_metrics = QFontMetrics(self.font())
        for i in range(self.count()):
            text = self.itemText(i)
            width = font_metrics.horizontalAdvance(text)
            max_width = max(max_width, width)
        extra_margin = 80
        max_width += extra_margin
        self.view().setMinimumWidth(max_width)
        super().showPopup()


class OptionCombo(QWidget):
    """A combobox for selecting options in the settings."""

    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCombo, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = None
        self.keys = []
        self.title = ""
        self.real_time = False
        self.combo = NoScrollCombo()
        self.combo.currentIndexChanged.connect(self.on_combo_change)
        self.current_id = None
        self.locked = False

        # add items
        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.fit_to_content()

    def update(self):
        """Prepare items"""
        # init from option data
        if self.option is not None:
            if "label" in self.option and self.option["label"] is not None and self.option["label"] != "":
                self.title = trans(self.option["label"])
            if "keys" in self.option:
                self.keys = self.option["keys"]
            if "value" in self.option:
                self.value = self.option["value"]
                self.current_id = self.value
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

        # add items
        if type(self.keys) is list:
            for item in self.keys:
                if type(item) is dict:
                    for key, value in item.items():
                        if not isinstance(key, str):
                            key = str(key)
                        if key.startswith("separator::"):
                            self.combo.addSeparator(value)
                        else:
                            self.combo.addItem(value, key)
                else:
                    # Support simple string keys including "separator::" entries
                    if isinstance(item, str) and item.startswith("separator::"):
                        self.combo.addSeparator(item.split("separator::", 1)[1])
                    else:
                        self.combo.addItem(item, item)
        elif type(self.keys) is dict:
            for key, value in self.keys.items():
                if not isinstance(key, str):
                    key = str(key)
                if key.startswith("separator::"):
                    self.combo.addSeparator(value)
                else:
                    self.combo.addItem(value, key)

        # Ensure a valid non-separator selection after population
        self._apply_initial_selection()

    def _apply_initial_selection(self):
        """
        Ensures that after building the list the combobox does not end up on a separator.
        Prefers self.current_id if present; otherwise selects the first valid non-separator.
        Signals are suppressed during this operation.
        """
        # lock on_change during initial selection
        prev_locked = self.locked
        self.locked = True
        try:
            index = -1
            if self.current_id is not None and self.current_id != "":
                index = self.combo.findData(self.current_id)
            if index == -1:
                index = self.combo.first_valid_index()
            if index != -1:
                self.combo.setCurrentIndex(index)
            else:
                # No valid items, clear selection
                self.combo.setCurrentIndex(-1)
        finally:
            self.locked = prev_locked

    def set_value(self, value):
        """
        Set value

        :param value: value
        """
        if not value:
            return
        index = self.combo.findData(value)
        if index != -1:
            self.combo.setCurrentIndex(index)
        else:
            # If requested value is not present, keep current selection but make sure it is valid.
            self.combo.ensure_valid_current()

    def get_value(self):
        """
        Get value

        :return: value
        """
        return self.current_id

    def set_keys(self, keys, lock: bool = False):
        """
        Set keys

        :param keys: keys
        :param lock: lock current value if True
        """
        if lock:
            self.locked = True  # lock on_change
        self.keys = keys
        self.option["keys"] = keys
        self.combo.clear()
        self.update()
        # After rebuilding, guarantee a non-separator selection
        self.combo.ensure_valid_current()
        if lock:
            self.locked = False

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        :return:
        """
        if self.locked:
            return

        # If somehow a separator got focus, correct it immediately and do not propagate invalid IDs
        if self.combo.is_separator(index):
            self.locked = True
            corrected = self.combo.ensure_valid_current()
            self.locked = False
            if corrected == -1:
                # Nothing valid to select
                self.current_id = None
                return
            index = corrected

        self.current_id = self.combo.itemData(index)
        self.window.controller.config.combo.on_update(self.parent_id, self.id, self.option, self.current_id)

    def fit_to_content(self):
        """Fit to content"""
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)