#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
# ================================================== #

import datetime
from typing import Optional

from pygpt_net.core.events import BaseEvent, Event
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

    def handle(self, event: BaseEvent):
        """
        Handle events

        :param event: BaseEvent: Event to handle
        """
        name = event.name

        # on input begin, unlock experts and reset evaluation steps
        if name == Event.CTX_END:
            mode = event.data.get("mode", "")
            if (mode not in self.window.controller.chat.input.no_ctx_idx_modes
                    and not self.window.controller.agent.legacy.enabled()):
                self.window.controller.idx.on_ctx_end(event.ctx, mode=mode)  # update ctx DB index
                # disabled in agent mode here to prevent loops, handled in agent flow internally if agent mode

    def get_modes_keys(self) -> list:
        """
        Get list of available modes

        :return: list of modes
        """
        return [
            {"chat": trans('toolbox.llama_index.mode.chat')},
            {"query": trans('toolbox.llama_index.mode.query')},
            {"retrieval": trans('toolbox.llama_index.mode.retrieval')},
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
        """Select current idx on list."""
        idx = self.window.core.config.get('llama.idx.current')
        if idx is None:
            self.current_idx = None
            return
        if self.window.ui.nodes['indexes.select'].has_key(idx):
            self.window.ui.nodes['indexes.select'].set_value(idx)
            self.current_idx = idx
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
        """Update list and inject the runtime-only current-project index."""
        items = list(self.window.core.config.get('llama.idx.list') or [])
        if self.window.core.idx.project.get_current_group_id() is not None:
            items.insert(0, {
                'id': self.window.core.idx.project.VIRTUAL_ID,
                'name': trans('idx.current_project'),
            })
        self.window.ui.toolbox.indexes.update(items)

    def auto_idx_allowed(self, mode: str) -> bool:
        """
        Check if auto idx is allowed

        :param mode: mode name
        :return: True if allowed
        """
        modes = self.window.core.config.get('llama.idx.auto.modes')
        if isinstance(modes, str):
            modes_list = [item.strip() for item in modes.split(',') if item.strip()]
        elif isinstance(modes, (list, tuple, set)):
            modes_list = [str(item).strip() for item in modes if str(item).strip()]
        else:
            modes_list = []
        return mode in modes_list

    def on_ctx_end(
            self,
            ctx: Optional[CtxItem] = None,
            mode: Optional[str] = None,
            sync: bool = False
    ):
        """Apply real-time auto-index policy after a conversation turn."""
        auto_policy = self.window.core.config.get('llama.idx.auto', 'off')
        # Compatibility guard for a config that reaches runtime before the
        # 2.8.8 config normalizer has persisted the legacy bool value.
        if isinstance(auto_policy, bool):
            auto_policy = 'all' if auto_policy else 'off'
        if auto_policy not in ('off', 'all', 'projects'):
            auto_policy = 'off'
        if auto_policy == 'off':
            return
        if mode is not None and not self.auto_idx_allowed(mode):
            return
        if self.window.controller.kernel.stopped():
            return

        # Prefer the context that actually emitted CTX_END. The active UI
        # context may already have changed while a streamed response was finishing.
        meta = None
        meta_id = getattr(ctx, 'meta_id', None) if ctx is not None else None
        if meta_id is not None:
            meta = self.window.core.ctx.get_meta_by_id(meta_id)
        if meta is None:
            meta = self.window.core.ctx.get_current_meta()
        if meta is None:
            return
        group_id = getattr(meta, 'group_id', None)
        in_project = group_id is not None and int(group_id) > 0
        per_project = bool(self.window.core.config.get('llama.idx.auto.project', True))

        # The policy controls where conversation auto-indexing is active.
        if auto_policy == 'projects' and not in_project:
            return

        # When isolation is enabled, a conversation inside a project is routed
        # exclusively to that project's virtual index instead of global targets.
        if in_project and per_project:
            self.indexer.index_project(int(group_id), from_last=True, sync=sync, silent=True)
            return

        targets = self.window.core.config.get('llama.idx.auto.index', 'base')
        if isinstance(targets, str):
            indexes = [item.strip() for item in targets.split(',') if item.strip()]
        elif isinstance(targets, (list, tuple, set)):
            indexes = [str(item).strip() for item in targets if str(item).strip()]
        else:
            indexes = []
        for idx in indexes:
            self.indexer.index_ctx_realtime(meta, idx, sync=sync)

    def after_index(self, idx: Optional[str] = None):
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
        """Refresh runtime index choices after context/project changes."""
        self.select_default()
        self.locked = True
        try:
            self.update_list()
        finally:
            self.locked = False
        self.select_current()

    def change_locked(self) -> bool:
        """
        Check if change is locked

        :return: True if locked
        """
        return self.locked

    def reload(self):
        """Reload indexer"""
        self.setup()

    def on_idx_start(self, show_global_stop: bool = True):
        """
        Called on indexing started.

        :param show_global_stop: show the global bottom STOP button
        """
        self.stop = False
        if show_global_stop:
            self.window.controller.ui.stop_action = "idx"
            self.window.controller.ui.show_global_stop()
        else:
            self.window.controller.ui.stop_action = None
            self.window.controller.ui.hide_global_stop()

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
        self.window.controller.ui.stop_action = None
        self.window.controller.ui.hide_global_stop()

    def index_selected(self) -> bool:
        """
        Check if any index is selected

        :return: True if selected
        """
        return self.current_idx is not None and self.current_idx != "_"

    def get_current(self) -> str:
        """
        Get current index name

        :return: Current index name
        """
        return self.current_idx

    def is_stopped(self) -> bool:
        """
        Check if indexing is stopped

        :return: True if stopped
        """
        return self.stop
