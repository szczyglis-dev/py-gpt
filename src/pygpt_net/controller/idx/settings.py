#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 05:00:00                  #
# ================================================== #

import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QSizePolicy

from pygpt_net.ui.widget.element.button import ContextMenuButton
from pygpt_net.ui.widget.element.help import HelpLabel
from pygpt_net.utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Indexes settings controller

        :param window: Window instance
        """
        self.window = window

    def append(self, content, options, fields):
        """
        Append extra settings to settings dialog (section: llama-index)

        :param content: settings widgets layout
        :param options: settings widgets
        :param fields: settings options config fields
        """
        btns = QHBoxLayout()
        self.window.ui.nodes['idx.btn.db.index_all'] = ContextMenuButton(trans('settings.llama.extra.btn.idx_db_all'))  # index DB (all)
        self.window.ui.nodes['idx.btn.db.index_all'].action = self.idx_db_all_context_menu
        self.window.ui.nodes['idx.btn.db.index_update'] = ContextMenuButton(trans('settings.llama.extra.btn.idx_db_update'))  # index DB (only update)
        self.window.ui.nodes['idx.btn.db.index_update'].action = self.idx_db_update_context_menu
        self.window.ui.nodes['idx.btn.db.index_files'] = ContextMenuButton(trans('settings.llama.extra.btn.idx_files_all'))  # index files (data)
        self.window.ui.nodes['idx.btn.db.index_files'].action = self.idx_data_context_menu

        last_str = '---'
        if self.window.core.config.has('llama.idx.db.last'):
            last_ts = int(self.window.core.config.get('llama.idx.db.last'))
            if last_ts > 0:
                # convert timestamp to datetime
                last_str = datetime.datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d %H:%M:%S')

        txt = trans('idx.last') + ": " + last_str
        self.window.ui.nodes['idx.db.last_updated'] = QLabel(txt)
        btns.addWidget(self.window.ui.nodes['idx.btn.db.index_all'])
        btns.addWidget(self.window.ui.nodes['idx.btn.db.index_update'])
        btns.addWidget(self.window.ui.nodes['idx.btn.db.index_files'])

        # offline loaders
        self.window.ui.nodes['idx.db.settings.loaders'] = \
            QLabel("\nBuilt-in data loaders: text, " + ", ".join(self.window.core.idx.indexing.loaders.keys()))
        self.window.ui.nodes['idx.db.settings.loaders'].setWordWrap(True)
        # add to layout
        self.window.ui.nodes['idx.db.settings.legend.head'] = QLabel(trans('settings.llama.extra.btn.idx_head'))
        self.window.ui.nodes['idx.db.settings.legend.head']\
            .setStyleSheet(self.window.controller.theme.style('text_bold'))
        self.window.ui.nodes['idx.db.settings.legend'] = HelpLabel(trans('settings.llama.extra.legend'), self.window)
        self.window.ui.nodes['idx.db.settings.legend'].setWordWrap(True)
        content.addWidget(self.window.ui.nodes['idx.db.settings.legend.head'])
        content.addLayout(btns)
        content.addWidget(self.window.ui.nodes['idx.db.settings.legend'])
        content.addWidget(self.window.ui.nodes['idx.db.last_updated'])
        content.addWidget(self.window.ui.nodes['idx.db.settings.loaders'])

    def idx_db_all_context_menu(self, parent, pos):
        """
        Index DB (all) btn context menu

        :param parent: parent widget (button)
        :param pos: mouse  position
        """
        menu = QMenu(parent)
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for idx in idxs:
                id = idx['id']
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(lambda checked=False, id=id:
                                         self.window.controller.idx.indexer.index_ctx_from_ts(id, 0))
        menu.exec_(parent.mapToGlobal(pos))

    def idx_db_update_context_menu(self, parent, pos):
        """
        Index DB (update) btn context menu

        :param parent: parent widget (button)
        :param pos: mouse  position
        """
        menu = QMenu(parent)
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for idx in idxs:
                id = idx['id']
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(lambda checked=False, id=id:
                                         self.window.controller.idx.indexer.index_ctx_current(id))
        menu.exec_(parent.mapToGlobal(pos))

    def idx_data_context_menu(self, parent, pos):
        """
        Index files (data) btn context menu

        :param parent: parent widget (button)
        :param pos: mouse  position
        """
        menu = QMenu(parent)
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for idx in idxs:
                id = idx['id']
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(lambda checked=False, id=id:
                                         self.window.controller.idx.indexer.index_all_files(id))
        menu.exec_(parent.mapToGlobal(pos))
