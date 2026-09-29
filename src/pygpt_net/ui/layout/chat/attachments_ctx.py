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
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QStandardItem, QStandardItemModel, QIcon, QAction
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QRadioButton, QCheckBox, QWidget, QMenu, QWidgetAction, QButtonGroup

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
        self._options_menu = None
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

        self.window.ui.nodes['input.attachments.ctx.mode.label'] = HelpLabel(
            trans('attachments.ctx.label'),
            self._options_state_holder,
        )
        self.window.ui.nodes['input.attachments.ctx.mode.full'] = QRadioButton(
            trans('attachments.ctx.mode.full'),
            self._options_state_holder,
        )
        self.window.ui.nodes['input.attachments.ctx.mode.full'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_FULL_CONTEXT
            ))
        self.window.ui.nodes['input.attachments.ctx.mode.query'] = QRadioButton(
            trans('attachments.ctx.mode.query'),
            self._options_state_holder,
        )
        self.window.ui.nodes['input.attachments.ctx.mode.query'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_QUERY_CONTEXT
            ))
        self.window.ui.nodes['input.attachments.ctx.mode.query_summary'] = QRadioButton(
            trans('attachments.ctx.mode.summary'),
            self._options_state_holder,
        )
        self.window.ui.nodes['input.attachments.ctx.mode.query_summary'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_QUERY_CONTEXT_SUMMARY
            ))
        self.window.ui.nodes['input.attachments.ctx.mode.off'] = QRadioButton(
            trans('attachments.ctx.mode.off'),
            self._options_state_holder,
        )
        self.window.ui.nodes['input.attachments.ctx.mode.off'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_DISABLED
            ))

        self.window.ui.nodes['input.attachments.native_upload'] = QCheckBox(
            trans('attachments.ctx.native_upload'),
            self._options_state_holder,
        )
        self.window.ui.nodes['input.attachments.native_upload'].toggled.connect(
            lambda enabled: self.window.controller.chat.attachment.toggle_native_upload(enabled)
        )
        self.window.ui.nodes['attachments_ctx.btn.options'] = self._create_options_button()

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_ctx.btn.clear'])
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_ctx.btn.options'])

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments.ctx'])
        layout.addWidget(self.window.ui.nodes['attachments_ctx'])
        layout.addLayout(buttons_layout)

        return layout

    def _create_options_button(self) -> QPushButton:
        # Same native QPushButton styling as the Clear/Add buttons next to it.
        btn = QPushButton(QIcon(':/icons/more_horizontal.svg'), '', self.window)
        btn.setObjectName('attachmentsCtxOptionsButton')
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setToolTip(trans('attachments.options.label'))
        btn.clicked.connect(self.action_show_options)
        return btn

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

    def action_show_options(self):
        """Open context options and keep the popup open for radios and checkboxes."""
        btn = self.window.ui.nodes.get('attachments_ctx.btn.options')
        if btn is None:
            return

        nodes = self.window.ui.nodes
        menu = QMenu(btn)
        menu.setObjectName('attachmentsCtxOptionsMenu')

        header = QAction(trans('attachments.ctx.label'), menu)
        header.setEnabled(False)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)
        menu.addAction(header)
        menu.addSeparator()

        group = QButtonGroup(menu)
        group.setExclusive(True)
        ctrl = self.window.controller.chat.attachment
        modes = (
            ('input.attachments.ctx.mode.full', 'attachments.ctx.mode.full', ctrl.MODE_FULL_CONTEXT),
            ('input.attachments.ctx.mode.query', 'attachments.ctx.mode.query', ctrl.MODE_QUERY_CONTEXT),
            ('input.attachments.ctx.mode.query_summary', 'attachments.ctx.mode.summary', ctrl.MODE_QUERY_CONTEXT_SUMMARY),
            ('input.attachments.ctx.mode.off', 'attachments.ctx.mode.off', ctrl.MODE_DISABLED),
        )
        for node_key, locale_key, mode in modes:
            node = nodes.get(node_key)
            if node is None:
                continue
            self._add_persistent_radio(
                menu,
                group,
                trans(locale_key),
                node.isChecked(),
                lambda key=node_key, value=mode: self._select_mode(key, value),
            )

        menu.addSeparator()
        native_upload = nodes.get('input.attachments.native_upload')
        if native_upload is not None:
            self._add_persistent_checkbox(
                menu,
                trans('attachments.ctx.native_upload'),
                native_upload.isChecked(),
                lambda checked=False, node=native_upload: node.setChecked(bool(checked)),
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
