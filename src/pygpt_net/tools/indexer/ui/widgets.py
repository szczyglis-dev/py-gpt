#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from typing_extensions import override

from PySide6.QtWidgets import QApplication, QMenu, QHeaderView

from pygpt_net.ui.dialog.db import DataBrowser
from pygpt_net.ui.widget.lists.db import DatabaseList
from pygpt_net.utils import trans


class IdxBrowseList(DatabaseList):

    def adjustColumns(self):
        """Adjust columns width"""
        last_column = self.model().columnCount() - 1
        self.horizontalHeader().setSectionResizeMode(last_column, QHeaderView.Stretch)

    def create_context_menu(self, parent):
        """
        Create context menu

        :param parent: Parent
        """

        def copy_to_clipboard():
            index = parent.currentIndex()
            if index.isValid():
                value = index.sibling(index.row(), 1).data(
                    Qt.DisplayRole)
                QApplication.clipboard().setText(value)

        def delete_row():
            index = parent.currentIndex()
            if index.isValid():
                id = index.sibling(index.row(), 0).data(
                    Qt.DisplayRole)
                self.window.tools.get("indexer").delete_db_idx(int(id))

        menu = QMenu()
        copy_action = menu.addAction(trans("tool.indexer.db.copy"))
        delete_action = menu.addAction(trans("tool.indexer.db.remove"))
        copy_action.triggered.connect(copy_to_clipboard)
        delete_action.triggered.connect(delete_row)
        menu.exec_(QCursor.pos())

class IdxBrowser(DataBrowser):
    @override
    def get_tables(self) -> dict:
        """
        Get tables configuration

        :return: Tables dictionary
        """
        data = self.window.tools.get("indexer").get_tables()
        tables = {k: v for k, v in data.items() if k in [
            "idx_ctx", "idx_file", "idx_external"]}
        return tables

    @override
    def get_filters(self):
        return {
            "idx": self.window.tools.get("indexer").current_idx,
            "store": self.window.core.config.get("llama.idx.storage"),
        }

    @override
    def get_table_name(self, selected_text):
        keys = self.get_tables().keys()
        mapping = {
            "idx_file": "Files",
            "idx_external": "Web",
            "idx_ctx": "Context",
        }
        for key in keys:
            if mapping[key] == selected_text:
                return key

    @override
    def get_table_names(self):
        return [
            "Files",
            "Web",
            "Context",
        ]

    @override
    def get_default_table(self):
        """
        Get default table

        :return: Default table name
        """
        return "idx_file"

    @override
    def set_list_widget(self):
        self.window.ui.nodes["tool.indexer.browse"] = IdxBrowseList(self.window)

    @override
    def get_list_widget(self):
        return self.window.ui.nodes["tool.indexer.browse"]

    @override
    def is_editable(self) -> bool:
        return False

    @override
    def is_inline(self) -> bool:
        return True