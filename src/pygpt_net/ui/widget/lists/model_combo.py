#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 16:35:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QPushButton, QMenu

from pygpt_net.ui.widget.lists.base_list_combo import BaseListCombo
from pygpt_net.utils import trans


class ModelCombo(BaseListCombo):
    def __init__(self, window=None, id=None):
        """
        Model select menu

        :param window: main window
        :param id: input id
        """
        super(ModelCombo, self).__init__(window, id)

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        """
        if not self.initialized or self.locked:
            return
        self.current_id = self.combo.itemData(index)
        self.window.controller.model.select(self.current_id)


class CompactModelCombo(QPushButton):
    """Compact runtime model selector used in the chat input controls row.

    It intentionally exposes the same small public API as ``ModelCombo``
    (``set_keys`` / ``set_value`` / ``get_value`` / ``has_key``), so the model
    controller does not need a second selection path after moving the selector
    out of the toolbox.
    """

    MAX_LABEL_WIDTH = 220

    def __init__(self, window=None, id: str = None, parent=None):
        super().__init__(parent)
        self.window = window
        self.id = id
        self.current_id = None
        self.keys = {}
        self._menu = None

        self.setObjectName("chatInputModel")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFlat(True)
        self.setIcon(QIcon())
        self.setToolTip(trans("input.model.tooltip"))
        self.clicked.connect(self._show_menu)

    def set_keys(self, keys):
        """Replace available models while preserving the current selection."""
        self.keys = keys or {}
        current = self.window.core.config.get("model") if self.window is not None else self.current_id
        if current is not None:
            self.current_id = current
        self._refresh_text()

    def set_value(self, value):
        """Update the selected model without dispatching a selection event."""
        self.current_id = value
        self._refresh_text()

    def get_value(self):
        return self.current_id

    def has_key(self, name: str) -> bool:
        if isinstance(self.keys, dict):
            return name in self.keys and not str(name).startswith(("separator::", "section::"))
        if isinstance(self.keys, list):
            for item in self.keys:
                if isinstance(item, dict):
                    if name in item:
                        return True
                elif item == name:
                    return True
        return False

    def fit_to_content(self):
        """Compatibility no-op: width is fitted by ``_refresh_text``."""
        self._refresh_text()

    def _label_for(self, value) -> str:
        if value is None:
            return ""
        if isinstance(self.keys, dict):
            label = self.keys.get(value)
            if label is not None:
                return str(label)
        elif isinstance(self.keys, list):
            for item in self.keys:
                if isinstance(item, dict) and value in item:
                    return str(item[value])
                if item == value:
                    return str(item)
        return str(value)

    def _refresh_text(self):
        label = self._label_for(self.current_id)
        if not label and self.window is not None:
            model_id = self.window.core.config.get("model")
            label = self._label_for(model_id)
            if model_id is not None:
                self.current_id = model_id

        if not label:
            label = trans("toolbox.model.label")

        fm = self.fontMetrics()
        display = fm.elidedText(label, Qt.ElideMiddle, self.MAX_LABEL_WIDTH)
        text = f"{display}  ▴"
        self.setText(text)
        self.setToolTip(trans("input.model.tooltip"))
        self.ensurePolished()
        text_width = fm.horizontalAdvance(text)
        # Keep enough room for the complete label + arrow. Horizontal padding is
        # intentionally kept small in QSS so model and reasoning form a compact
        # pair without clipping either control.
        width = max(56, min(
            self.MAX_LABEL_WIDTH + 34,
            max(self.sizeHint().width(), text_width + 10),
        ))
        self.setFixedWidth(width)

    def _iter_entries(self):
        if isinstance(self.keys, dict):
            yield from self.keys.items()
            return
        if isinstance(self.keys, list):
            for item in self.keys:
                if isinstance(item, dict):
                    yield from item.items()
                else:
                    yield item, item

    def _show_menu(self):
        if self.window is None:
            return

        menu = QMenu(self)
        menu.setObjectName("chatInputModelMenu")
        group = QActionGroup(menu)
        group.setExclusive(True)

        has_items = False
        for key, label in self._iter_entries():
            key_str = str(key)
            if key_str.startswith(("separator::", "section::")):
                if has_items:
                    menu.addSeparator()
                header = QAction(str(label), menu)
                header.setEnabled(False)
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                menu.addAction(header)
                continue

            has_items = True
            action = QAction(str(label), menu)
            action.setCheckable(True)
            action.setChecked(key == self.current_id)
            group.addAction(action)
            action.triggered.connect(
                lambda checked=False, value=key: self._select_model(value, checked)
            )
            menu.addAction(action)

        if not has_items:
            menu.deleteLater()
            return

        self._menu = menu
        menu.aboutToHide.connect(self._clear_menu)
        menu.adjustSize()
        size = menu.sizeHint()
        global_pos = self.mapToGlobal(QPoint(self.width() - size.width(), -size.height()))
        menu.popup(global_pos)

    def _select_model(self, model_id, checked=True):
        if not checked:
            return
        self.window.controller.model.select(model_id)
        # ``select`` can be rejected while generation is locked. Reflect the
        # effective config value in either case instead of leaving a stale check.
        self.set_value(self.window.core.config.get("model"))

    def _clear_menu(self):
        menu = self._menu
        self._menu = None
        if menu is not None:
            menu.deleteLater()
