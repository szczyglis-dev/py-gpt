#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
from pygpt_net.ui.widget.option.combo import SeparatorComboBox
from pygpt_net.ui.widget.lists.base_list_combo import BaseListCombo


class ModePopupCombo(SeparatorComboBox):
    """Plain mode selector with a compact menu and no search field."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup_menu = None

    def wheelEvent(self, event):
        event.ignore()

    def showPopup(self):
        if self._popup_menu is not None:
            self._popup_menu.close()
        menu = QMenu(self)
        menu.setObjectName('modeSelectorMenu')
        # Keep the selector width as a minimum; let QMenu measure translated
        # labels and styled padding so longer mode names remain fully visible.
        menu.setMinimumWidth(self.width())
        # Checked state supplies the current-row background; no indicator is drawn.
        menu.setStyleSheet('QMenu#modeSelectorMenu { margin: 0; padding: 0; }'
                           'QMenu#modeSelectorMenu::item { padding: 4px 24px 4px 10px; min-height: 0; }'
                           'QMenu#modeSelectorMenu::indicator { width: 0; height: 0; image: none; }'
                           'QMenu#modeSelectorMenu::item:checked {'
                           ' background-color: rgba(128, 128, 128, 24); }')
        for index in range(self.count()):
            if self.itemData(index, self._SEP_ROLE):
                menu.addSeparator()
                continue
            action = QAction(self.itemText(index), menu)
            enabled = bool(self.model().flags(self.model().index(index, 0)) & Qt.ItemIsEnabled)
            action.setEnabled(enabled)
            if enabled:
                action.setCheckable(True)
                action.setChecked(index == self.currentIndex())
                action.triggered.connect(lambda checked=False, row=index: self.setCurrentIndex(row))
            else:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
            menu.addAction(action)
        self._popup_menu = menu
        menu.aboutToHide.connect(self._clear_popup)
        menu.popup(self.mapToGlobal(QPoint(0, self.height())))

    def hidePopup(self):
        if self._popup_menu is not None:
            self._popup_menu.close()

    def _clear_popup(self):
        menu = self._popup_menu
        self._popup_menu = None
        if menu is not None:
            menu.deleteLater()



class ModeCombo(BaseListCombo):
    def __init__(self, window=None, id=None):
        """
        Mode select menu

        :param window: main window
        :param id: input id
        """
        super(ModeCombo, self).__init__(window, id)

    def create_combo(self):
        return ModePopupCombo(self.window)

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        """
        if not self.initialized or self.locked:
            return
        self.current_id = self.combo.itemData(index)
        self.window.controller.mode.select(self.current_id)
