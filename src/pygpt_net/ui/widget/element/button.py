#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 17:35:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QMenu

from pygpt_net.utils import trans


class ContextMenuButton(QPushButton):
    def __init__(self, title, parent=None, action=None):
        super().__init__(title, parent)
        self.action = action

    def mousePressEvent(self, event):
        btn = event.button()
        if btn == Qt.LeftButton or btn == Qt.RightButton:
            self.action(self, event.pos())
        else:
            super().mousePressEvent(event)


class ButtonPopupMenu(QPushButton):
    """Reusable icon-only button that opens a popup menu above itself."""

    def __init__(
        self,
        parent=None,
        menu_builder=None,
        tooltip_key: str = 'action.options',
        object_name: str = None,
        menu_object_name: str = None,
    ):
        super().__init__(QIcon(':/icons/more_horizontal.svg'), '', parent)
        self.menu_builder = menu_builder
        self.tooltip_key = tooltip_key
        self.menu_object_name = menu_object_name
        self._popup_menu = None

        if object_name:
            self.setObjectName(object_name)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.retranslate()
        self.clicked.connect(self.show_popup_menu)

    def retranslate(self):
        """Refresh the default tooltip after a runtime language change."""
        self.setToolTip(trans(self.tooltip_key))

    def set_menu_builder(self, menu_builder):
        """Replace the callback used to populate a freshly-created QMenu."""
        self.menu_builder = menu_builder

    def show_popup_menu(self):
        """Build and show a fresh menu aligned to the button's right edge."""
        self._clear_popup_menu()

        menu = QMenu(self)
        if self.menu_object_name:
            menu.setObjectName(self.menu_object_name)
        if self.menu_builder is not None:
            self.menu_builder(menu)

        if menu.isEmpty():
            menu.deleteLater()
            return

        self._popup_menu = menu
        menu.aboutToHide.connect(self._clear_popup_menu)
        menu.adjustSize()
        size = menu.sizeHint()
        global_pos = self.mapToGlobal(QPoint(self.width() - size.width(), -size.height()))
        menu.popup(global_pos)

    def _clear_popup_menu(self):
        menu = self._popup_menu
        self._popup_menu = None
        if menu is not None:
            menu.deleteLater()


class LabelButton(QPushButton):
    """Borderless text or icon action styled by the current theme."""

    def __init__(self, title='', parent=None):
        super().__init__(title, parent)
        self.setProperty('class', 'LabelButton')
        self.setCursor(Qt.PointingHandCursor)

    def initStyleOption(self, option):
        super().initStyleOption(option)
        if option.text and not option.icon.isNull():
            # Add breathing room to icon labels without changing their text
            # (translations, accessible names and callers keep the original).
            option.text = '\u2002' + option.text


class NewCtxButton(LabelButton):
    _icon_add = None
    _icon_folder_filled = None

    def __init__(self, title: str = None, window=None):
        super().__init__(title)
        self.window = window
        self.setObjectName('newChatButton')
        self.setIcon(QIcon(":/icons/new_chat.svg"))
        self.setToolTip(trans('ctx.new.tooltip'))
        self.clicked.connect(lambda: self.window.controller.ctx.new(force=False))

    @classmethod
    def _ensure_icons(cls):
        if cls._icon_add is None:
            cls._icon_add = QIcon(":/icons/new_chat.svg")
            cls._icon_folder_filled = QIcon(":/icons/folder_filled.svg")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.new_context_menu(self, event.pos())
            event.accept()
            return
        super().mousePressEvent(event)

    def new_context_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        type(self)._ensure_icons()
        group_id = self.window.controller.ctx.group_id
        menu = QMenu(parent)
        if group_id is not None and group_id > 0:
            group_name = self.window.controller.ctx.get_group_name(group_id)
            act_new_in_group = menu.addAction(type(self)._icon_add, trans('action.ctx.new.in_group').format(group=group_name))
            act_new_in_group.triggered.connect(
                lambda checked=False, id=group_id: self.window.controller.ctx.new(force=False, group_id=id)
            )
        act_new = menu.addAction(type(self)._icon_add, trans('action.ctx.new'))
        act_new.triggered.connect(
            lambda checked=False: self.window.controller.ctx.new_ungrouped()
        )
        act_new_group = menu.addAction(type(self)._icon_folder_filled, trans('menu.file.group.new'))
        act_new_group.triggered.connect(
            lambda checked=False: self.window.controller.ctx.new_group()
        )
        menu.exec_(parent.mapToGlobal(pos))
        menu.deleteLater()


class SyncButton(QPushButton):
    _icon_download = None

    def __init__(self, title: str = None, window=None):
        super().__init__(title)
        self.window = window
        self.clicked.connect(
            lambda: self.window.controller.remote_store.batch.import_files_assistant_current()
        )

    @classmethod
    def _ensure_icons(cls):
        if cls._icon_download is None:
            cls._icon_download = QIcon(":/icons/download.svg")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.new_context_menu(self, event.pos())
        else:
            super().mousePressEvent(event)

    def new_context_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        type(self)._ensure_icons()
        menu = QMenu(parent)
        act_current = menu.addAction(type(self)._icon_download, trans('attachments_uploaded.btn.sync.current'))
        act_current.triggered.connect(
            lambda checked=False: self.window.controller.remote_store.batch.import_files_assistant_current()
        )
        act_all = menu.addAction(type(self)._icon_download, trans('attachments_uploaded.btn.sync.all'))
        act_all.triggered.connect(
            lambda checked=False: self.window.controller.remote_store.batch.import_files_assistant_all()
        )
        menu.exec_(parent.mapToGlobal(pos))
        menu.deleteLater()
