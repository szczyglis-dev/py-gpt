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

import os

from PySide6.QtCore import Qt, QPoint, QTimer
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
        if os.name == "nt":
            # A translucent top-level QMenu can get a thick native frame/shadow
            # on Windows. Keep this compact popup opaque and frameless instead;
            # its background and outline are provided entirely by QSS.
            menu.setAttribute(Qt.WA_TranslucentBackground, False)
            menu.setWindowFlag(Qt.FramelessWindowHint, True)
            # menu.setWindowFlag(Qt.NoDropShadowWindowHint, True)
        else:
            menu.setAttribute(Qt.WA_TranslucentBackground, True)
        group = QActionGroup(menu)
        group.setExclusive(True)

        has_items = False
        grouped = bool(self.window.core.config.get("model.group_providers", True))
        target_menu = menu
        provider_label = None
        for key, label in self._iter_entries():
            key_str = str(key)
            if key_str.startswith(("separator::", "section::")):
                if grouped:
                    provider_label = str(label)
                    target_menu = None
                    continue
                if has_items:
                    menu.addSeparator()
                header = QAction(str(label), menu)
                header.setEnabled(False)
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                menu.addAction(header)
                continue

            if grouped and target_menu is None:
                target_menu = QMenu(provider_label, menu)
                menu.addMenu(target_menu)
                target_menu.setObjectName("chatInputModelMenu")
            has_items = True
            action = QAction(str(label), target_menu)
            action.setCheckable(True)
            action.setChecked(key == self.current_id)
            group.addAction(action)
            action.triggered.connect(
                lambda checked=False, value=key: self._select_model(value, checked)
            )
            target_menu.addAction(action)

        if not has_items:
            menu.deleteLater()
            return

        self._menu = menu
        menu.aboutToHide.connect(self._clear_menu)
        menu.adjustSize()
        size = menu.sizeHint()
        global_pos = self._centered_menu_pos(size.width(), size.height())
        menu.popup(global_pos)
        # QMenu may switch to a multi-column layout only after it is shown when
        # the model list is taller than the available screen. Recenter once more
        # using the final native popup width so the menu stays exactly centered.
        QTimer.singleShot(0, lambda current=menu: self._recenter_visible_menu(current))

    def _menu_anchor(self):
        """Anchor provider submenus over the selector, flat lists over the input."""
        if self.window.core.config.get("model.group_providers", True):
            return self
        return self.window.ui.nodes.get("input") or self

    def _menu_x(self, anchor, width: int) -> int:
        if self.window.core.config.get("model.group_providers", True):
            return anchor.mapToGlobal(QPoint(anchor.width(), 0)).x() - width
        center = anchor.mapToGlobal(QPoint(anchor.width() // 2, 0))
        return int(center.x() - width / 2)

    def _centered_menu_pos(self, width: int, height: int) -> QPoint:
        """Return an upward popup position aligned with its selection anchor."""
        anchor = self._menu_anchor()

        x = self._menu_x(anchor, max(0, int(width)))
        y = self.mapToGlobal(QPoint(0, -max(0, int(height)))).y()

        screen = anchor.screen() or self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            max_x = available.right() - max(0, int(width)) + 1
            x = max(available.left(), min(x, max_x))
        return QPoint(x, y)

    def _recenter_visible_menu(self, menu: QMenu):
        """Align the popup again after Qt finalizes its real geometry."""
        if self._menu is not menu or not menu.isVisible():
            return
        width = menu.width() or menu.sizeHint().width()
        anchor = self._menu_anchor()
        x = self._menu_x(anchor, width)
        screen = menu.screen() or anchor.screen() or self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            max_x = available.right() - width + 1
            x = max(available.left(), min(x, max_x))
        menu.move(x, menu.y())

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
