#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.13 06:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.utils import trans


class Indexer:
    def __init__(self, window=None):
        """
        Indexing controller

        :param window: Window instance
        """
        self.window = window
        self.tmp_idx = None

    def update_explorer(self):
        """Update file explorer view"""
        all_idx_data = self.window.core.idx.get_idx_data()  # get all files data, from all indexes
        self.window.ui.nodes['output_files'].model.update_idx_status(all_idx_data)

    def update_idx_status(self, idx: str = "base"):
        """
        Update index status in config

        :param idx: Index name
        """
        idx_data = {}
        if self.window.core.config.has('llama.idx.status'):
            idx_data = self.window.core.config.get('llama.idx.status')
        if idx not in idx_data:
            idx_data[idx] = {}
        idx_data['last_ts'] = int(datetime.datetime.now().timestamp())
        self.window.core.config.set('llama.idx.status', idx_data)
        self.window.core.config.save()

    def index_ctx_meta(self, ctx_idx, idx):
        """
        Index context meta (threaded)

        :param ctx_idx: context idx on list
        :param idx: index name
        """
        meta_id = self.window.core.ctx.get_id_by_idx(ctx_idx)
        self.window.update_status(trans('idx.status.indexing'))

        worker = IndexWorker()
        worker.window = self.window
        worker.content = meta_id
        worker.idx = idx
        worker.type = "db_meta"
        worker.signals.finished.connect(self.handle_finished_db_meta)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def index_ctx_current(self, idx, force: bool = False, silent: bool = False):
        """
        Index current context (threaded)

        :param idx: index name
        :param force: force index
        :param silent: silent mode
        """
        from_ts = 0
        if self.window.core.config.has('llama.idx.db.last'):
            from_ts = int(self.window.core.config.get('llama.idx.db.last'))
        if not silent:
            self.window.update_status(trans('idx.status.indexing'))
        self.index_ctx_from_ts(idx, from_ts, force=force, silent=silent)

    def index_ctx_from_ts_confirm(self, ts):
        """
        Index context from timestamp (force execute)

        :param ts: timestamp from (updated_ts)
        """
        # get stored index name
        if self.tmp_idx is None:
            return
        self.window.update_status(trans('idx.status.indexing'))
        self.index_ctx_from_ts(self.tmp_idx, ts, True)
        self.tmp_idx = None

    def index_ctx_from_ts(self, idx, ts, force: bool = False, silent: bool = False):
        """
        Index context from timestamp (threaded)

        :param idx: index name
        :param ts: timestamp from (updated_ts)
        :param force: force index
        :param silent: silent mode
        """
        self.tmp_idx = idx  # store tmp index name (for confirmation)
        if not force:
            self.window.ui.dialogs.confirm('idx.index.db.all', ts, trans('idx.confirm.db.content'))
            return
        worker = IndexWorker()
        worker.window = self.window
        worker.content = ts
        worker.idx = idx
        worker.type = "db_current"
        worker.silent = silent
        worker.signals.finished.connect(self.handle_finished_db_current)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def index_path(self, path: str, idx: str = "base"):
        """
        Index all files in path (threaded)

        :param path: path to index
        :param idx: index name
        """
        self.window.update_status(trans('idx.status.indexing'))
        worker = IndexWorker()
        worker.window = self.window
        worker.content = path
        worker.idx = idx
        worker.type = "file"
        worker.signals.finished.connect(self.handle_finished_file)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def index_all_files(self, idx: str, force: bool = False):
        """
        Index all files in data directory (threaded)

        :param idx: index name
        :param force: force index
        """
        self.tmp_idx = idx  # store tmp index name (for confirmation)

        path = self.window.core.config.get_user_dir('data')
        if not force:
            self.window.ui.dialogs.confirm('idx.index.files.all', idx, trans('idx.confirm.files.content').
                                           replace('{dir}', path))
            return
        self.index_path(path, idx)

    def clear_by_idx(self, idx: int):
        """
        Clear index by list idx

        :param idx: on list idx
        """
        idx_name = self.window.core.idx.get_by_idx(idx)
        self.clear(idx_name)

    def clear(self, idx: str, force: bool = False):
        """
        Clear index data

        :param idx: index name
        :param force: force clear
        """
        path = os.path.join(self.window.core.config.get_user_dir('idx'), idx)
        if not force:
            self.window.ui.dialogs.confirm('idx.clear', idx, trans('idx.confirm.clear.content').
                                           replace('{dir}', path))
            return

        # remove current index
        self.window.update_status(trans('idx.status.truncating'))
        QApplication.processEvents()  # update UI to show status

        try:
            result = self.window.core.idx.remove_index(idx)
            if result:
                self.window.core.idx.clear(idx)
                self.window.update_status(trans('idx.status.truncate.success'))
                self.update_explorer()  # update file explorer view

                # reset DB update time if db index was cleared
                if self.window.core.config.has('llama.idx.db.index'):
                    if self.window.core.config.get('llama.idx.db.index') == idx:
                        self.window.core.config.set('llama.idx.db.last', 0)
                        self.window.core.config.save()
            else:
                self.window.update_status(trans('idx.status.truncate.error'))
        except Exception as e:
            print(e)
            self.window.update_status(e)

    @Slot(object)
    def handle_error(self, e: any):
        """
        Handle thread error signal

        :param e: error message
        """
        self.window.ui.dialogs.alert(str(e))
        self.window.update_status(str(e))
        print(e)

    @Slot(str, object, object)
    def handle_finished_db_current(self, idx: str, num: int, errors: list, silent: bool = False):
        """
        Handle indexing finished signal

        :param idx: index name
        :param num: number of indexed records
        :param errors: errors
        :param silent: silent mode (no msg and status update)
        """
        if num > 0:
            msg = trans('idx.status.success') + f" {num}"

            # store last DB update timestamp
            self.window.core.config.set('llama.idx.db.index', idx)
            self.window.core.config.set('llama.idx.db.last', int(datetime.datetime.now().timestamp()))
            self.window.core.config.save()
            self.update_idx_status(idx)
            self.window.controller.idx.after_index(idx)  # post-actions (update UI, etc.)
            if not silent:
                self.window.update_status(msg)
                self.window.ui.dialogs.alert(msg)
        else:
            self.window.update_status(trans('idx.status.empty'))

        if len(errors) > 0:
            self.window.ui.dialogs.alert("\n".join(errors))

    @Slot(str, object, object, bool)
    def handle_finished_db_meta(self, idx: str, num: int, errors: list, silent: bool = False):
        """
        Handle indexing finished signal

        :param idx: index name
        :param num: number of indexed records
        :param errors: errors
        :param silent: silent mode (no msg and status update)
        """
        if num > 0:
            msg = trans('idx.status.success') + f" {num}"
            self.update_idx_status(idx)
            self.window.controller.idx.after_index(idx)  # post-actions (update UI, etc.)
            if not silent:
                self.window.update_status(msg)
                self.window.ui.dialogs.alert(msg)
        else:
            self.window.update_status(trans('idx.status.empty'))

        if len(errors) > 0:
            self.window.ui.dialogs.alert("\n".join(errors))

    @Slot(str, object, object, bool)
    def handle_finished_file(self, idx: str, files: dict, errors: list, silent: bool = False):
        """
        Handle indexing finished signal

        :param idx: index name
        :param files: indexed files
        :param errors: errors
        :param silent: silent mode (no msg and status update)
        """
        num = len(files)
        if num > 0:
            msg = trans('idx.status.success') + f" {num}"
            self.window.core.idx.append(idx, files)  # append files list to index
            self.update_idx_status(idx)
            self.window.controller.idx.after_index(idx)  # post-actions (update UI, etc.)
            if not silent:
                self.window.update_status(msg)
                self.window.ui.dialogs.alert(msg)
        else:
            self.window.update_status(trans('idx.status.empty'))

        if len(errors) > 0:
            self.window.ui.dialogs.alert("\n".join(errors))


class IndexWorkerSignals(QObject):
    finished = Signal(str, object, object, bool)  # idx, result, errors, silent mode
    error = Signal(object)


class IndexWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(IndexWorker, self).__init__()
        self.signals = IndexWorkerSignals()
        self.window = None
        self.content = None
        self.idx = None
        self.type = None
        self.silent = False

    @Slot()
    def run(self):
        """Indexer thread"""
        try:
            result = {}
            errors = []
            is_log = False
            if self.window.core.config.has("llama.log") and self.window.core.config.get("llama.log"):
                is_log = True
            model = "gpt-3.5-turbo"  # prepare model for indexing
            config = self.window.core.idx.get_idx_config(self.idx)
            if config is not None and 'model_embed' in config:
                tmp_model = config['model_embed']
                if tmp_model is not None \
                        and tmp_model != "" \
                        and tmp_model != "---" \
                        and tmp_model != "_":
                    model = tmp_model
            # log indexing
            if is_log:
                print("[LLAMA-INDEX] Indexing data...")
                print("[LLAMA-INDEX] Idx: {}, type: {}, content: {}, model: {}".format(self.idx, self.type, self.content, model))
            # execute indexing
            if self.type == "file":
                result, errors = self.window.core.idx.index_files(self.idx, self.content, model=model)
            elif self.type == "db_meta":
                result, errors = self.window.core.idx.index_db_by_meta_id(self.idx, self.content, model=model)
            elif self.type == "db_current":
                result, errors = self.window.core.idx.index_db_from_updated_ts(self.idx, self.content, model=model)
            if is_log:
                print("[LLAMA-INDEX] Finished indexing.")
            self.signals.finished.emit(self.idx, result, errors, self.silent)
        except Exception as e:
            self.signals.error.emit(e)
