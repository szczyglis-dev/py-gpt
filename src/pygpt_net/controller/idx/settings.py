#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import datetime
from typing import Dict, Any

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QLayout

from pygpt_net.ui.widget.element.button import ContextMenuButton
from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Index settings controller

        :param window: Window instance
        """
        self.window = window

    def append_tabs(self) -> list:
        """
        Return additional tabs list

        :return: list of tab IDs
        """
        return ["update"]

    def append(
            self,
            content: Dict[str, QLayout],
            widgets: Dict[str, Any],
            options: Dict[str, Any],
    ):
        """
        Append extra settings to settings dialog (section: llama-index)

        :param content: settings widgets layout
        :param widgets: settings widgets
        :param options: settings options config fields
        """
        btns = QHBoxLayout()
        self.window.ui.nodes['idx.btn.db.index_all'] = \
            ContextMenuButton(trans('settings.llama.extra.btn.idx_db_all'))  # index DB (all)
        self.window.ui.nodes['idx.btn.db.index_all'].action = self.idx_db_all_context_menu
        self.window.ui.nodes['idx.btn.db.index_update'] = \
            ContextMenuButton(trans('settings.llama.extra.btn.idx_db_update'))  # index DB (only update)
        self.window.ui.nodes['idx.btn.db.index_update'].action = self.idx_db_update_context_menu
        self.window.ui.nodes['idx.btn.db.index_files'] = \
            ContextMenuButton(trans('settings.llama.extra.btn.idx_files_all'))  # index files (data)
        self.window.ui.nodes['idx.btn.db.index_files'].action = self.idx_data_context_menu

        self.window.ui.nodes['idx.api.warning'] = TitleLabel(trans('settings.llama.extra.api.warning'))
        self.window.ui.nodes['idx.api.warning'].setWordWrap(True)

        self.window.ui.nodes['idx.db.last_updated'] = QLabel("")
        self.update_text_last_updated()
        btns.addWidget(self.window.ui.nodes['idx.btn.db.index_all'])
        btns.addWidget(self.window.ui.nodes['idx.btn.db.index_update'])
        btns.addWidget(self.window.ui.nodes['idx.btn.db.index_files'])

        # offline loaders
        self.window.ui.nodes['idx.db.settings.loaders'] = QLabel("")
        self.update_text_loaders()
        self.window.ui.nodes['idx.db.settings.loaders'].setWordWrap(True)
        self.window.ui.nodes['idx.db.settings.legend.head'] = TitleLabel(trans('settings.llama.extra.btn.idx_head'))
        self.window.ui.nodes['idx.db.settings.legend'] = HelpLabel(trans('settings.llama.extra.legend'), self.window)
        self.window.ui.nodes['idx.db.settings.legend'].setWordWrap(True)

        if "data_loaders" in content:
            content["data_loaders"].addWidget(self.window.ui.nodes['idx.db.settings.loaders'])

        if "update" in content:
            content["update"].addWidget(self.window.ui.nodes['idx.db.settings.legend.head'])
            content["update"].addLayout(btns)
            content["update"].addWidget(self.window.ui.nodes['idx.db.settings.legend'])
            content["update"].addWidget(self.window.ui.nodes['idx.db.last_updated'])
            content["update"].addWidget(self.window.ui.nodes['idx.api.warning'])

    def update_text_last_updated(self):
        """Update last updated text"""
        last_str = trans('settings.llama.extra.db.never')
        if self.window.core.config.has('llama.idx.db.last'):
            last_ts = int(self.window.core.config.get('llama.idx.db.last'))
            if last_ts > 0:
                # convert timestamp to datetime
                last_str = datetime.datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d %H:%M:%S')

        txt = trans('idx.last') + ": " + last_str
        self.window.ui.nodes['idx.db.last_updated'].setText(txt)

    def update_text_loaders(self):
        """Update text loaders list"""
        list_file = []
        list_web = []
        list_file.append("- Txt/raw files (txt)")
        providers = self.window.core.idx.indexing.get_data_providers()
        for id in providers:
            loader = providers[id]
            if "file" in loader.type:
                list_file.append("- " + loader.name + " (" + ", ".join(loader.extensions) + ") - file_" + loader.id)
            if "web" in loader.type:
                list_web.append("- " + loader.name + " - web_" + loader.id)
        list_file = sorted(list_file)
        list_web = sorted(list_web)
        files_str = "\n".join(list_file)
        web_str = "\n".join(list_web)
        info = trans('settings.llama.extra.loaders') + ":\n\nFiles:\n" + files_str + "\n\nWeb/external:\n" + web_str
        self.window.ui.nodes['idx.db.settings.loaders'].setText(info)

    def update_idx_choices(self):
        """Update index choices"""
        option = self.window.controller.settings.editor.get_option("agent.idx")
        option["keys"] = self.window.controller.config.placeholder.get_idx()
        self.window.ui.config["config"]["agent.idx"].combo.clear()
        self.window.ui.config["config"]["agent.idx"].option = option
        self.window.ui.config["config"]["agent.idx"].update()

    def idx_db_all_context_menu(self, parent, pos):
        """
        Index DB (all) btn context menu

        :param parent: parent widget (button)
        :param pos: mouse position
        """
        menu = QMenu(parent)
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for idx in idxs:
                id = idx['id']
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.index_ctx_from_ts(id, 0)
                )
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
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.index_ctx_current(id))
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
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.index_all_files(id))
        menu.exec_(parent.mapToGlobal(pos))
