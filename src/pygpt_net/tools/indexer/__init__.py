#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.20 19:00:00                  #
# ================================================== #

import datetime
import json

from PySide6.QtCore import Slot
from PySide6.QtGui import QAction, QIcon, QTextCursor
from sqlalchemy import text

from pygpt_net.tools.base import BaseTool
from pygpt_net.utils import trans

from .ui.dialogs import DialogBuilder


class IndexerTool(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Indexer tool

        :param window: Window instance
        """
        super(IndexerTool, self).__init__(*args, **kwargs)
        self.id = "indexer"  # unique tool id
        self.dialog = None
        self.opened = False
        self.current_idx = "base"

    def attach(self, window):
        """
        Attach window to tool

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup tool"""
        self.window.idx_logger_message.connect(self.handle_log)  # connect logger

    def update(self):
        """Update"""
        pass

    def open(self):
        """Open dialog window"""
        self.window.ui.dialogs.open('tool.indexer', width=800, height=600)
        self.opened = True
        self.refresh()
        self.update()

    def close(self):
        """Close dialog window"""
        self.window.ui.dialogs.close('tool.indexer')
        self.opened = False

    def toggle(self):
        """Toggle dialog window"""
        if self.opened:
            self.close()
        else:
            self.open()

    def open_settings(self):
        """Open settings dialog"""
        self.window.controller.settings.open_section("llama-index")

    def show_hide(self, show: bool = True):
        """
        Show/hide dialog window

        :param show: show/hide
        """
        if show:
            self.open()
        else:
            self.close()

    def on_close(self):
        """On dialog close"""
        self.opened = False

    def on_exit(self):
        """On app exit"""
        pass

    def on_tab_changed(self, index):
        """
        On tab changed

        :param index: tab index
        """
        if index > 1:
            self.window.ui.nodes["tool.indexer.btn.idx"].hide()
        else:
            self.window.ui.nodes["tool.indexer.btn.idx"].show()
        self.refresh()

    def set_current_idx(self, idx, check: bool = True):
        """
        Set current index

        :param idx: index id
        :param check: check if index is valid
        """
        self.current_idx = idx
        self.refresh(check)

    def check_current_idx(self):
        """Check if current index is valid"""
        valid = False
        default = None
        indexes = self.window.core.config.get("llama.idx.list")
        for item in indexes:
            if item["id"] == self.current_idx:
                valid = True
            if default is None:
                default = item["id"]
        if not valid and self.current_idx != "-":
            self.current_idx = default

    def reload(self):
        """Reload indexes"""
        self.window.core.idx.indexing.reload_loaders()
        self.update_tab_web()
        self.window.ui.nodes["tool.indexer.idx"].set_keys(self.window.controller.config.placeholder.apply_by_id("idx"))
        self.set_current_idx(self.current_idx)
        self.window.ui.nodes["tool.indexer.idx"].set_value(self.current_idx)

    def refresh(self, check: bool = True):
        """
        Refresh dialog window

        :param check: check if index is valid
        """
        if check:
            self.check_current_idx()
        self.update_tabs()

    def on_reload(self):
        """On app profile reload"""
        self.reload()

    def update_tabs(self):
        """Update tabs"""
        self.window.ui.nodes["tool.indexer.provider"].setText(self.window.core.config.get("llama.idx.storage"))
        self.update_tab_ctx()
        self.update_tab_files()
        self.update_tab_browse()

    def update_tab_ctx(self):
        """Update context tab"""
        # get database
        db = self.window.core.db.get_db()

        # last meta ID
        last_meta_id = "-"
        query = "SELECT meta_id, updated_ts FROM idx_ctx WHERE idx=:idx AND store=:store ORDER BY meta_id DESC LIMIT 1"
        stmt = text(query).bindparams(idx=self.current_idx, store=self.window.core.config.get("llama.idx.storage"))
        with db.connect() as conn:
            results = conn.execute(stmt).fetchall()
            if results:
                row = results[0]._asdict()
                last_meta_id = str(row["meta_id"]) + " ({})".format(
                    datetime.datetime.fromtimestamp(row["updated_ts"]).strftime('%Y-%m-%d %H:%M:%S'))
        self.window.ui.nodes['tool.indexer.ctx.last_meta_id'].setText(last_meta_id)

        # last meta ts
        last_meta_ts = "-"
        query = "SELECT meta_id, updated_ts FROM idx_ctx WHERE idx=:idx AND store=:store ORDER BY updated_ts DESC LIMIT 1"
        stmt = text(query).bindparams(idx=self.current_idx, store=self.window.core.config.get("llama.idx.storage"))
        with db.connect() as conn:
            results = conn.execute(stmt).fetchall()
            if results:
                row = results[0]._asdict()
                last_meta_ts = str(row["meta_id"]) + " ({})".format(
                    datetime.datetime.fromtimestamp(row["updated_ts"]).strftime('%Y-%m-%d %H:%M:%S'))
        self.window.ui.nodes['tool.indexer.ctx.last_meta_ts'].setText(last_meta_ts)

        # auto-index enabled
        auto_str = trans("tool.indexer.tab.ctx.auto.no")
        if self.window.core.config.get("llama.idx.auto"):
            auto_str = trans("tool.indexer.tab.ctx.auto.yes") + " ({})".format(self.window.core.config.get("llama.idx.auto.index"))
        self.window.ui.nodes['tool.indexer.ctx.auto_enabled'].setText(auto_str)

        # last auto-index TS
        last_str = trans('settings.llama.extra.db.never')
        if self.window.core.config.has('llama.idx.db.last'):
            last_ts = int(self.window.core.config.get('llama.idx.db.last'))
            if last_ts > 0:
                last_str = datetime.datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d %H:%M:%S')
        self.window.ui.nodes['tool.indexer.ctx.last_auto'].setText(last_str)

    def update_tab_files(self):
        """
        Update files tab

        :return: list of available file loaders
        """
        list_file = []
        list_file.append("txt (plain-text files)")
        providers = self.window.core.idx.indexing.get_data_providers()
        for id in providers:
            loader = providers[id]
            if "file" in loader.type:
                for ext in loader.extensions:
                    list_file.append(ext)
        list_file = sorted(list_file)
        files_str = ", ".join(list_file)
        info = trans("tool.indexer.loaders") + ": " + files_str
        self.window.ui.nodes['tool.indexer.file.loaders'].setText(info)
        return list_file

    def update_tab_browse(self):
        """Update browse tab"""
        self.window.ui.nodes['tool.indexer.browser'].update_table_view()

    def update_tab_web(self):
        """Update web tab"""
        loaders = self.window.core.idx.indexing.get_external_config()
        for loader in loaders:
            params = loaders[loader]
            for k in params:
                key_path = "tool.indexer.web.loader.config." + loader + "." + k
                value = ""
                try:
                    if params[k]["value"] is not None:
                        if params[k]["type"] == "list" and isinstance(params[k]["value"], list):
                            value = ", ".join(params[k]["value"])
                        elif params[k]["type"] == "dict" and isinstance(params[k]["value"], dict):
                            value = json.dumps(params[k]["value"])
                        else:
                            value = str(params[k]["value"])
                except Exception as e:
                    self.window.core.debug.log(e)
                if key_path in self.window.ui.nodes:
                    self.window.ui.nodes[key_path].setText(value)
                    self.window.ui.nodes[key_path].value = value

    def idx_ctx_db_all(self):
        """Index all context data"""
        # self.clear_log()
        self.window.controller.idx.indexer.index_ctx_from_ts(self.current_idx, 0)

    def idx_ctx_db_update(self):
        """Index context data from last update"""
        # self.clear_log()
        self.window.controller.idx.indexer.index_ctx_current(self.current_idx)

    def index_data(self, force: bool = False):
        """
        Index data

        :param force: force indexing
        """
        if self.current_idx == "-" or self.current_idx is None or self.current_idx == "_":
            self.window.ui.dialogs.alert(trans("tool.indexer.alert.no_idx"))
            return
        tab = self.window.ui.tabs['tool.indexer'].currentIndex()
        # self.clear_log()
        if tab == 0:
            self.index_files(force)
        elif tab == 1:
            self.index_web(force)

    def index_files(self, force: bool = False):
        """
        Index files

        :param force: force indexing
        """
        is_recursive = self.window.ui.nodes["tool.indexer.file.options.recursive"].isChecked()
        is_replace = self.window.ui.nodes["tool.indexer.file.options.replace"].isChecked()
        dir = self.window.ui.nodes["tool.indexer.file.path_dir"].value
        files = self.window.ui.nodes["tool.indexer.file.path_file"].value
        paths = []
        if dir:
            paths.append(dir)
        if files:
            paths.extend(files)
        if len(paths) == 0:
            self.window.ui.dialogs.alert(trans("tool.indexer.alert.no_files"))
            return
        if not force:
            self.window.ui.dialogs.confirm(
                type="idx.tool.index",
                id=0,
                msg=trans("tool.indexer.confirm.idx"),
            )
            return
        self.window.controller.idx.indexer.index_paths(
            paths,
            self.current_idx,
            is_replace,
            is_recursive,
        )

    def index_web(self, force: bool = False):
        """
        Index web data

        :param force: force indexing
        """
        input_params = {}
        input_config = {}
        is_replace = self.window.ui.nodes["tool.indexer.web.options.replace"].isChecked()
        loader = self.window.ui.nodes["tool.indexer.web.loader"].get_value()
        if not loader:
            self.window.ui.dialogs.alert(trans("tool.indexer.alert.no_loader"))
            return
        loaders = self.window.core.idx.indexing.get_external_instructions()
        if loader in loaders:
            params = loaders[loader]
            for k in params["args"]:
                key_path = "tool.indexer.web.loader.option." + loader + "." + k
                if key_path in self.window.ui.nodes:
                    input_params[k] = self.window.ui.nodes[key_path].text()

        loaders = self.window.core.idx.indexing.get_external_config()
        if loader in loaders:
            params = loaders[loader]
            for k in params:
                key_path = "tool.indexer.web.loader.config." + loader + "." + k
                type = params[k]["type"]
                if key_path in self.window.ui.nodes:
                    tmp_value = self.window.ui.nodes[key_path].text()
                    try:
                        if tmp_value:
                            if type == "int":
                                tmp_value = int(tmp_value)
                            elif type == "float":
                                tmp_value = float(tmp_value)
                            elif type == "bool":
                                if tmp_value.lower() in ["true", "1"]:
                                    tmp_value = True
                                else:
                                    tmp_value = False
                            elif type == "list":
                                tmp_value = tmp_value.split(",")
                            elif type == "dict":
                                tmp_value = json.loads(tmp_value)
                            input_config[k] = tmp_value
                    except Exception as e:
                        self.window.core.debug.log(e)
                        self.window.ui.dialogs.alert(e)
        if not force:
            self.window.ui.dialogs.confirm(
                type="idx.tool.index",
                id=0,
                msg=trans("tool.indexer.confirm.idx"),
            )
            return

        self.window.controller.idx.indexer.index_web(
            self.current_idx,
            loader,
            input_params,
            input_config,
            is_replace,
        )

    def on_finish_files(self):
        """On finish indexing files"""
        if self.window.ui.nodes["tool.indexer.file.options.clear"].isChecked():
            self.window.ui.nodes["tool.indexer.file.path_file"].clear()
            self.window.ui.nodes["tool.indexer.file.path_dir"].clear()
        print("Indexing files finished")

    def on_finish_web(self):
        """On finish indexing web"""
        print("Indexing web finished")

    def truncate_idx(self):
        """Truncate index"""
        self.window.controller.idx.indexer.clear(self.current_idx)

    def delete_db_idx(self, id: int, force: bool = False):
        """
        Delete index from database

        :param id: index id
        :param force: force deletion
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type="idx.tool.truncate",
                id=id,
                msg=trans("tool.indexer.confirm.remove"),
            )
            return
            
        table = self.window.ui.nodes['tool.indexer.browser'].get_current_table()
        query = "SELECT doc_id FROM {} WHERE id=:id".format(table)
        stmt = text(query).bindparams(id=id)
        with self.window.core.db.get_db().connect() as conn:
            results = conn.execute(stmt).fetchall()
            if results:
                result = results[0]._asdict()
                doc_id = result["doc_id"]

        # remove from db
        query = "DELETE FROM {} WHERE id=:id".format(table)
        stmt = text(query).bindparams(id=id)
        with self.window.core.db.get_db().begin() as conn:
            conn.execute(stmt)

        # remove from index
        if doc_id:
            self.window.core.idx.remove_doc(self.current_idx, doc_id)

        self.refresh()

    @Slot(object)
    def handle_log(self, data: any):
        """
        Handle log message

        :param data: message to log
        """
        self.log(data)

    def log(self, data: any):
        """
        Log message to console or logger window

        :param data: text to log
        """
        if not self.opened or data is None or str(data).strip() == "":
            return
        data = datetime.datetime.now().strftime('%H:%M:%S.%f') + ': ' + str(data)
        cur = self.window.ui.nodes["tool.indexer.status"].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(data) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertText("\n")
        self.window.ui.nodes["tool.indexer.status"].setTextCursor(cur)  # Update visible cursor

    def clear_log(self):
        """Clear log"""
        self.window.ui.nodes["tool.indexer.status"].clear()

    def get_tables(self) -> dict:
        """
        Get tables configuration

        :return: Tables dictionary
        """
        columns = {}
        columns["idx_ctx"] = [
            'id',
            'meta_id',
            'doc_id',
            'updated_ts',
        ]
        columns["idx_external"] = [
            'id',
            'content',
            'type',
            'doc_id',
            'updated_ts',
        ]
        columns["idx_file"] = [
            'id',
            'name',
            'path',
            'doc_id',
            'updated_ts',
        ]

        tables = {
            'idx_ctx': {
                'columns': columns["idx_ctx"],
                'sort_by': columns["idx_ctx"],
                'search_fields': ['id', 'doc_id', 'meta_id'],
                'timestamp_columns': ['updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'idx_file': {
                'columns': columns["idx_file"],
                'sort_by': columns["idx_file"],
                'search_fields': ['id', 'doc_id', 'name', 'path'],
                'timestamp_columns': ['updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'idx_external': {
                'columns': columns["idx_external"],
                'sort_by': columns["idx_external"],
                'search_fields': ['id', 'doc_id', 'content', 'type'],
                'timestamp_columns': ['updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
        }
        return tables

    def setup_menu(self) -> dict:
        """
        Setup main menu (Tools)

        :return dict with menu actions
        """
        actions = {}
        actions["indexer"] = QAction(
            QIcon(":/icons/db.svg"),
            trans("tool.indexer"),
            self.window,
            checkable=False,
        )
        actions["indexer"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = DialogBuilder(self.window)
        self.dialog.setup()

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.indexer': 'tool.indexer',  # menu key => translation key
            }
        }


