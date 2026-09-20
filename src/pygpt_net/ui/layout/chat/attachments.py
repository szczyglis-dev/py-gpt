#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 18:05:00                  #
# ================================================== #

import os
from functools import partial

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QStandardItemModel, QIcon, QAction
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QWidget, QMenu, QWidgetAction

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.attachment import AttachmentList
from pygpt_net.core.attachments.clipboard import AttachmentDropHandler
from pygpt_net.utils import trans


class Attachments:
    def __init__(self, window=None):
        """
        Attachments UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments'
        # Keep a strong reference to DnD handler(s)
        self._dnd_handlers = {}
        self._options_menu = None
        self._options_state_holder = None

    def setup(self) -> QVBoxLayout:
        """
        Setup attachments list

        :return: QVBoxLayout
        """
        self.setup_attachments()
        self.setup_buttons()

        buttons = QHBoxLayout()
        nodes = self.window.ui.nodes
        buttons.addWidget(nodes['attachments.btn.add'])
        buttons.addWidget(nodes['attachments.btn.add_url'])
        buttons.addWidget(nodes['attachments.btn.clear'])
        buttons.addStretch()
        buttons.addWidget(nodes['attachments.btn.options'])

        self.window.ui.nodes['tip.input.attachments'] = HelpLabel(trans('tip.input.attachments'), self.window)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments'])
        layout.addWidget(self.window.ui.nodes['attachments'])
        layout.addLayout(buttons)

        return layout

    def setup_buttons(self):
        """Setup buttons and hidden state widgets used by existing controllers."""
        nodes = self.window.ui.nodes
        ctrl = self.window.controller.attachment

        icon_add = QIcon(":/icons/add.svg")
        icon_close = QIcon(":/icons/close.svg")

        nodes['attachments.btn.add'] = QPushButton(icon_add, trans('attachments.btn.add'), self.window)
        nodes['attachments.btn.add_url'] = QPushButton(icon_add, trans('attachments.btn.add_url'), self.window)
        nodes['attachments.btn.clear'] = QPushButton(icon_close, trans('attachments.btn.clear'), self.window)

        nodes['attachments.btn.add'].clicked.connect(ctrl.open_add)
        nodes['attachments.btn.add_url'].clicked.connect(ctrl.open_add_url)
        nodes['attachments.btn.clear'].clicked.connect(partial(ctrl.clear, remove_local=True))

        # Keep the historic checkbox nodes because setup/mode/language controllers
        # already update them. They live in a permanently hidden holder; the popup
        # mirrors their state with native checkable QAction entries.
        self._options_state_holder = QWidget(self.window)
        self._options_state_holder.hide()

        nodes['attachments.send_clear'] = QCheckBox(trans('attachments.send_clear'), self._options_state_holder)
        nodes['attachments.send_clear'].toggled.connect(ctrl.toggle_send_clear)

        nodes['attachments.capture_clear'] = QCheckBox(trans('attachments.capture_clear'), self._options_state_holder)
        nodes['attachments.capture_clear'].toggled.connect(ctrl.toggle_capture_clear)

        nodes['attachments.auto_index'] = QCheckBox(trans('attachments.auto_index'), self._options_state_holder)
        nodes['attachments.auto_index'].toggled.connect(ctrl.toggle_auto_index)

        nodes['attachments.btn.options'] = self._create_options_button()

    def _create_options_button(self) -> QPushButton:
        # Deliberately use the regular QPushButton style, exactly like Add file,
        # Web and Clear. No flat/fixed-size override here.
        btn = QPushButton(QIcon(':/icons/more_horizontal.svg'), '', self.window)
        btn.setObjectName('attachmentsOptionsButton')
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolTip(trans('attachments.options.label'))
        btn.clicked.connect(self.action_show_options)
        return btn

    @staticmethod
    def _add_check_action(menu: QMenu, text: str, checked: bool, callback) -> QWidgetAction:
        """Add a checkbox row that does not close the menu when toggled."""
        checkbox = QCheckBox(text, menu)
        checkbox.setChecked(bool(checked))
        checkbox.toggled.connect(callback)

        holder = QWidget(menu)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(0)
        layout.addWidget(checkbox)

        action = QWidgetAction(menu)
        action.setDefaultWidget(holder)
        menu.addAction(action)
        return action

    def action_show_options(self):
        """Open attachment options; checkbox rows stay open when toggled."""
        btn = self.window.ui.nodes.get('attachments.btn.options')
        if btn is None:
            return

        nodes = self.window.ui.nodes
        menu = QMenu(btn)
        menu.setObjectName('attachmentsOptionsMenu')

        header = QAction(trans('attachments.options.label'), menu)
        header.setEnabled(False)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        menu.addAction(header)
        menu.addSeparator()

        auto_index = nodes.get('attachments.auto_index')
        if auto_index is not None:
            self._add_check_action(
                menu,
                trans('attachments.auto_index'),
                auto_index.isChecked(),
                lambda checked=False, node=auto_index: node.setChecked(bool(checked)),
            )

        send_clear = nodes.get('attachments.send_clear')
        if send_clear is not None:
            self._add_check_action(
                menu,
                trans('attachments.send_clear'),
                send_clear.isChecked(),
                lambda checked=False, node=send_clear: node.setChecked(bool(checked)),
            )

        capture_clear = nodes.get('attachments.capture_clear')
        # controller.ui.mode explicitly hides this option outside vision modes.
        # isHidden() reflects that explicit state even though the holder itself
        # is permanently hidden.
        if capture_clear is not None and not capture_clear.isHidden():
            self._add_check_action(
                menu,
                trans('attachments.capture_clear'),
                capture_clear.isChecked(),
                lambda checked=False, node=capture_clear: node.setChecked(bool(checked)),
            )

        self._options_menu = menu
        menu.aboutToHide.connect(self._clear_options_menu)
        menu.adjustSize()
        size = menu.sizeHint()
        global_pos = btn.mapToGlobal(QPoint(btn.width() - size.width(), -size.height()))
        menu.popup(global_pos)

    def _clear_options_menu(self):
        menu = self._options_menu
        self._options_menu = None
        if menu is not None:
            menu.deleteLater()

    def setup_attachments(self):
        """Setup attachments list"""
        self.window.ui.nodes[self.id] = AttachmentList(self.window)
        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

        # Drag & Drop: allow dropping files/images/urls/text directly onto the list
        try:
            self._dnd_handlers[self.id] = AttachmentDropHandler(
                self.window,
                self.window.ui.nodes[self.id],
                policy=AttachmentDropHandler.SWALLOW_ALL,
            )
        except Exception as e:
            try:
                self.window.core.debug.log(e)
            except Exception:
                pass

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 4, parent)
        model.setHorizontalHeaderLabels([
            trans('attachments.header.name'),
            trans('attachments.header.path'),
            trans('attachments.header.size'),
            trans('attachments.header.ctx'),
        ])
        return model

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        model = self.window.ui.models[self.id]
        rows = len(data)
        model.setRowCount(rows)

        exists = os.path.exists
        getsize = os.path.getsize
        sizeof_fmt = self.window.core.filesystem.sizeof_fmt

        model.beginResetModel()
        for i, (_, item) in enumerate(data.items()):
            path = item.path
            if item.type == AttachmentItem.TYPE_FILE and path and exists(path):
                size = sizeof_fmt(getsize(path))
            else:
                size = ""
            ctx_str = "YES" if item.ctx else ""

            model.setData(model.index(i, 0), item.name)
            model.setData(model.index(i, 1), path)
            model.setData(model.index(i, 2), size)
            model.setData(model.index(i, 3), ctx_str)
        model.endResetModel()

        if rows:
            model.dataChanged.emit(model.index(0, 0), model.index(rows - 1, 3), [])
