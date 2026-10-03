#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 18:15:00                  #
# ================================================== #

import os

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel, QIcon, QAction
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QRadioButton, QCheckBox, QWidget, QMenu, QWidgetAction, QButtonGroup

from pygpt_net.ui.widget.element.button import ButtonPopupMenu
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.attachment_ctx import AttachmentCtxList
from pygpt_net.utils import trans


class AttachmentsCtx:
    def __init__(self, window=None):
        """
        Attachments for CTX UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments_ctx'
        self._updating = False
        self._options_state_holder = None

    def setup(self) -> QVBoxLayout:
        """
        Setup list

        :return: QVBoxLayout
        """
        self.setup_attachments()

        self.window.ui.nodes['tip.input.attachments.ctx'] = HelpLabel(
            trans('tip.input.attachments.ctx'),
            self.window,
        )

        # Keep historic controls as hidden state carriers so all existing
        # setup/controller/language code continues to work unchanged.
        self._options_state_holder = QWidget(self.window)
        self._options_state_holder.hide()

        self.window.ui.nodes['attachments_ctx.btn.options'] = ButtonPopupMenu(
            self.window,
            menu_builder=self._build_options_menu,
            object_name='attachmentsCtxOptionsButton',
            menu_object_name='attachmentsCtxOptionsMenu',
        )

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_ctx.btn.clear'])
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_ctx.btn.options'])

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments.ctx'])
        layout.addWidget(self.window.ui.nodes['attachments_ctx'])
        layout.addLayout(buttons_layout)

        return layout

    def _select_mode(self, node_key: str, mode: str):
        node = self.window.ui.nodes.get(node_key)
        if node is not None:
            node.setChecked(True)
        self.window.controller.chat.attachment.switch_mode(mode)

    @staticmethod
    def _add_persistent_checkbox(menu: QMenu, text: str, checked: bool, callback) -> QWidgetAction:
        """Add a checkbox row without closing the popup after a click."""
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

    @staticmethod
    def _add_persistent_radio(
        menu: QMenu,
        group: QButtonGroup,
        text: str,
        checked: bool,
        callback,
    ) -> QWidgetAction:
        """Add an exclusive radio row without closing the popup after a click."""
        radio = QRadioButton(text, menu)
        radio.setChecked(bool(checked))
        group.addButton(radio)
        radio.toggled.connect(lambda enabled: callback() if enabled else None)

        holder = QWidget(menu)
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(0)
        layout.addWidget(radio)

        action = QWidgetAction(menu)
        action.setDefaultWidget(holder)
        menu.addAction(action)
        return action

    def _build_options_menu(self, menu: QMenu):
        """Populate context options; radio and checkbox rows remain open."""
        nodes = self.window.ui.nodes

        header = QAction(trans('attachments.ctx.label'), menu)
        header.setEnabled(False)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        menu.addAction(header)
        menu.addSeparator()

        full = QAction(trans('attachments.ctx.mode.full'), menu)
        full.setEnabled(False)
        menu.addAction(full)

    def setup_attachments(self):
        """Setup attachments uploaded list"""
        self.window.ui.nodes[self.id] = AttachmentCtxList(self.window)

        self.window.ui.nodes['attachments_ctx.btn.clear'] = QPushButton(
            QIcon(':/icons/close.svg'),
            trans('attachments_uploaded.btn.clear')
        )
        self.window.ui.nodes['attachments_ctx.btn.clear'].clicked.connect(
            lambda: self.window.controller.chat.attachment.clear()
        )

        self.window.ui.models[self.id] = self.create_model(self.window.ui.nodes[self.id])
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])
        self.window.ui.nodes[self.id].configureColumns()
        self.window.ui.models[self.id].itemChanged.connect(self.on_item_changed)

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 6, parent)
        model.setHeaderData(0, Qt.Horizontal, trans('attachments.header.active'))
        model.setHeaderData(1, Qt.Horizontal, trans('attachments.header.name'))
        model.setHeaderData(2, Qt.Horizontal, trans('attachments.header.path'))
        model.setHeaderData(3, Qt.Horizontal, trans('attachments.header.size'))
        model.setHeaderData(4, Qt.Horizontal, trans('attachments.header.length'))
        model.setHeaderData(5, Qt.Horizontal, trans('attachments.header.idx'))
        return model

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        model = self.window.ui.models[self.id]
        row_count = len(data)
        self._updating = True
        model.blockSignals(True)
        try:
            model.beginResetModel()
            model.setRowCount(row_count)

            m_index = model.index
            m_setData = model.setData
            tooltip_role = QtCore.Qt.ToolTipRole
            trans_indexed = trans('attachments.ctx.indexed')
            sizeof_fmt = self.window.core.filesystem.sizeof_fmt
            stat = os.stat

            for i, item in enumerate(data):
                name = item.get('name', 'No name')
                path = item.get('path', 'No path')
                uuid = item.get('uuid', '')
                length = '-'
                if 'length' in item:
                    length = str(item['length'])
                if 'tokens' in item:
                    length += ' / ~' + str(item['tokens'])
                idx_str = trans_indexed if item.get('indexed') else ''

                size = '-'
                if isinstance(path, str):
                    try:
                        st = stat(path)
                    except (OSError, ValueError, TypeError):
                        pass
                    else:
                        size = sizeof_fmt(st.st_size)
                if size == '-' and 'size' in item:
                    size = sizeof_fmt(item['size'])

                active_item = QStandardItem()
                active_item.setCheckable(True)
                active_item.setEditable(False)
                active_item.setTextAlignment(Qt.AlignCenter)
                active_item.setCheckState(
                    Qt.Checked if item.get('active', True) is not False else Qt.Unchecked
                )
                model.setItem(i, 0, active_item)

                idx_name = m_index(i, 1)
                m_setData(idx_name, 'uuid: ' + str(uuid), tooltip_role)
                m_setData(idx_name, name)
                m_setData(m_index(i, 2), path)
                m_setData(m_index(i, 3), size)
                m_setData(m_index(i, 4), length)
                m_setData(m_index(i, 5), idx_str)

            model.endResetModel()
        finally:
            model.blockSignals(False)
            self._updating = False

    def on_item_changed(self, item: QStandardItem):
        """Persist Active checkbox changes for context attachments."""
        if self._updating or item is None or item.column() != 0:
            return
        active = item.checkState() == Qt.Checked
        self.window.controller.chat.attachment.set_active_by_idx(item.row(), active)
