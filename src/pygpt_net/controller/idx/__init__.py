#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

import datetime

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans
from .common import Common
from .indexer import Indexer
from .settings import Settings


class Idx:
    def __init__(self, window=None):
        """
        Indexes controller

        :param window: Window instance
        """
        self.window = window
        self.settings = Settings(window)
        self.common = Common(window)
        self.indexer = Indexer(window)
        self.current_idx = "base"
        self.current_mode = "chat"
        self.locked = False
        self.stop = False

    def setup(self):
        """Setup indexer"""
        self.window.core.idx.load()
        self.indexer.update_explorer()
        self.common.setup()

        # restore last index
        last_idx = self.window.core.config.get('llama.idx.current')
        if last_idx is not None:
            self.current_idx = last_idx

        # restore mode
        last_mode = self.window.core.config.get('llama.idx.mode')
        if last_mode is not None:
            self.current_mode = last_mode

        self.locked = True  # lock update from combo box on start
        self.update()
        self.locked = False

    def get_modes_keys(self) -> list:
        """
        Get list of available modes

        :return: list of modes
        """
        return [
            {"chat": trans('toolbox.llama_index.mode.chat')},
            {"query": trans('toolbox.llama_index.mode.query')},
        ]

    def select_mode(self, mode: str):
        """
        Select llama index mode

        :param mode: key of the list
        """
        # check if mode change is not locked
        if self.change_locked():
            return

        self.window.core.config.set('llama.idx.mode', mode)
        self.current_mode = mode

        # update all layout
        self.window.controller.ui.update()

    def select(self, idx: int):
        """
        Select idx by list idx

        :param idx: idx of the list (row idx)
        """
        # check if idx change is not locked
        if self.change_locked():
            return
        self.set_by_idx(idx)

        # update all layout
        self.window.controller.ui.update()

    def select_by_id(self, id: int):
        """
        Select idx by list idx

        :param id: id of the list (row idx)
        """
        # check if idx change is not locked
        if id is None or id == "-":
            self.current_idx = None
            id = None

        if self.change_locked():
            return

        self.window.core.config.set('llama.idx.current', id)
        self.current_idx = id

        # update all layout
        self.window.controller.ui.update()

    def set(self, idx: str):
        """
        Set idx by name

        :param idx: idx name
        """
        self.window.core.config.set('llama.idx.current', idx)
        self.current_idx = idx

    def idx_db_update_by_idx(self, idx: int):
        """
        Index new records in database (update)

        :param idx: idx of the list (row idx)
        """
        idx = self.window.core.idx.get_by_idx(idx)
        if idx is None:
            return
        self.indexer.index_ctx_current(idx)

    def idx_db_all_by_idx(self, idx: int):
        """
        Index all records in database

        :param idx: idx of the list (row idx)
        """
        idx = self.window.core.idx.get_by_idx(idx)
        if idx is None:
            return
        self.indexer.index_ctx_from_ts(idx, 0)

    def idx_files_all_by_idx(self, idx: int):
        """
        Index all files in database

        :param idx: idx of the list (row idx)
        """
        idx = self.window.core.idx.get_by_idx(idx)
        if idx is None:
            return
        self.indexer.index_all_files(idx)

    def set_by_idx(self, idx: int):
        """
        Set idx by list idx

        :param idx: idx of the list (row idx)
        """
        idx = self.window.core.idx.get_by_idx(idx)
        if idx is None:
            return
        self.window.core.config.set('llama.idx.current', idx)
        self.current_idx = idx

    def select_current(self):
        """Select current idx on list"""
        idx = self.window.core.config.get('llama.idx.current')
        if idx is None:
            return
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            if self.window.ui.nodes['indexes.select'].has_key(idx):
                self.window.ui.nodes['indexes.select'].set_value(idx)
                return
        self.current_idx = None  # clear if no index on list

    def select_current_mode(self):
        """Select current mode on list"""
        mode = self.window.core.config.get('llama.idx.mode')
        if mode is None:
            return
        self.window.ui.nodes['llama_index.mode.select'].set_value(mode)

    def select_default(self):
        """Set default idx"""
        idx = self.window.core.config.get('llama.idx.current')
        """
        if idx is None:
            idx = self.window.core.idx.get_default_idx()
            if idx is not None:
                self.current_idx = idx
        """

    def update(self):
        """Update lists"""
        self.select_default()
        self.locked = True  # lock update from combo box
        self.update_list()  # update idx list
        self.locked = False
        self.select_current()  # select current idx on list
        self.select_current_mode()  # select current mode on list

    def update_list(self):
        """Update list"""
        items = self.window.core.config.get('llama.idx.list')
        if items is not None:
            self.window.ui.toolbox.indexes.update(items)

    def auto_idx_allowed(self, mode: str) -> bool:
        """
        Check if auto idx is allowed

        :param mode: mode name
        :return: True if allowed
        """
        modes = self.window.core.config.get('llama.idx.auto.modes')
        if modes is not None:
            modes_list = modes.replace(" ", "").split(',')
            if mode in modes_list:
                return True
        return False

    def on_ctx_end(self, ctx: CtxItem = None, mode: str = None, sync: bool = False):
        """
        After context item updated (request + response received)

        :param ctx: Context item instance
        :param mode: Mode
        :param sync: Synchronous call
        """
        # ignore if disallowed mode
        if mode is not None and not self.auto_idx_allowed(mode):
            return

        # ignore if manually stopped
        if self.window.controller.chat.input.stop:
            return

        idx = "base"  # default index
        if self.window.core.config.has('llama.idx.auto') and self.window.core.config.get('llama.idx.auto'):
            if self.window.core.config.has('llama.idx.auto.index'):
                idx = self.window.core.config.get('llama.idx.auto.index')

            # index items from previously indexed time only
            current_ctx = self.window.core.ctx.current
            if current_ctx is not None:
                meta = self.window.core.ctx.get_meta_by_id(current_ctx)
                if meta is not None:
                    self.indexer.index_ctx_realtime(meta, idx, sync=sync)

    def after_index(self, idx: str = None):
        """
        Called after index (update things, etc...)

        :param idx: index name
        """
        self.indexer.update_explorer()  # update file explorer view

        # update last indexing timestamp label
        last_str = '---'
        if self.window.core.config.has('llama.idx.db.last'):
            last_ts = int(self.window.core.config.get('llama.idx.db.last'))
            if last_ts > 0:
                last_str = datetime.datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d %H:%M:%S')

        txt = trans('idx.last') + ": " + last_str
        self.window.ui.nodes['idx.db.last_updated'].setText(txt)

    def refresh(self):
        """Update list"""
        self.select_default()

    def change_locked(self) -> bool:
        """
        Check if change is locked

        :return: True if locked
        """
        return self.locked

    def reload(self):
        """Reload indexer"""
        self.setup()

    def on_idx_start(self):
        """
        Called on indexing started

        :param idx: index name
        """
        self.stop = False
        self.window.controller.ui.stop_action = "idx"
        self.window.controller.ui.show_global_stop()

    def on_idx_end(self):
        """
        Called on indexing started

        :param idx: index name
        """
        self.stop = False
        self.window.controller.ui.stop_action = None
        self.window.controller.ui.hide_global_stop()

    def on_idx_error(self):
        """
        Called on indexing started

        :param idx: index name
        """
        self.stop = False
        self.window.controller.ui.stop_action = None
        self.window.controller.ui.hide_global_stop()

    def force_stop(self):
        """Force stop indexing"""
        print("Force stop indexing...")
        self.stop = True

    def is_stopped(self) -> bool:
        """
        Check if indexing is stopped

        :return: True if stopped
        """
        return self.stop
