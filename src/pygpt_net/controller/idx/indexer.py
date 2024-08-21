#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.21 19:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.core.idx.worker import IndexWorker
from pygpt_net.item.ctx import CtxMeta
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
        self.window.controller.files.update_explorer()

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

    def index_ctx_meta_confirm(self, ctx_idx: int):
        """
        Index context meta (confirm)

        :param ctx_idx: context idx on list
        """
        # get stored index name
        if self.tmp_idx is None:
            return

        self.index_ctx_meta(
            ctx_idx,
            self.tmp_idx,
            True,
        )

    def index_ctx_meta(
            self,
            meta_id: int,
            idx: str,
            force: bool = False
    ):
        """
        Index context meta (threaded)

        :param meta_id: context meta id
        :param idx: index name
        :param force: force index
        """
        if not force:
            self.tmp_idx = idx  # store tmp index name (for confirmation)
            content = trans('idx.confirm.db.content') + "\n" + trans('idx.token.warn')
            self.window.ui.dialogs.confirm(
                type='idx.index.db',
                id=meta_id,
                msg=content,
            )
            return

        meta = self.window.core.ctx.get_meta_by_id(meta_id)
        from_ts = meta.indexed
        self.window.update_status(trans('idx.status.indexing'))

        worker = IndexWorker()
        worker.window = self.window
        worker.content = meta_id
        worker.idx = idx
        worker.type = "db_meta"
        worker.from_ts = from_ts
        worker.signals.finished.connect(self.handle_finished_db_meta)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)
        self.window.controller.idx.on_idx_start()  # on start

    def index_ctx_current(
            self,
            idx: str,
            force: bool = False,
            silent: bool = False
    ):
        """
        Index current context (threaded)

        :param idx: index name
        :param force: force index
        :param silent: silent mode
        """
        from_ts = 0
        if self.window.core.config.has('llama.idx.db.last'):
            from_ts = int(self.window.core.config.get('llama.idx.db.last'))

        if not silent and force:
            self.window.update_status(trans('idx.status.indexing'))

        self.index_ctx_from_ts(
            idx,
            from_ts,
            force=force,
            silent=silent,
        )

    def index_ctx_realtime(
            self,
            meta: CtxMeta,
            idx: str,
            sync: bool = False
    ):
        """
        Index current appended context (threaded) - realtime

        :param meta: context meta
        :param idx: index name
        :param sync: sync mode
        """
        worker = IndexWorker()
        worker.window = self.window
        worker.content = meta.id
        worker.idx = idx
        worker.type = "db_meta"
        worker.from_ts = meta.indexed
        worker.silent = True
        worker.signals.finished.connect(self.handle_finished_db_meta)
        worker.signals.error.connect(self.handle_error)

        if sync:
            worker.run()
        else:
            self.window.threadpool.start(worker)

    def index_ctx_from_ts_confirm(self, ts: int):
        """
        Index context from timestamp (force execute)

        :param ts: timestamp from (updated_ts)
        """
        # get stored index name
        if self.tmp_idx is None:
            return
        self.window.update_status(trans('idx.status.indexing'))

        self.index_ctx_from_ts(
            self.tmp_idx,
            ts,
            True,
        )
        self.tmp_idx = None

    def index_ctx_from_ts(
            self,
            idx: str,
            ts: int,
            force: bool = False,
            silent: bool = False
    ):
        """
        Index context from timestamp (threaded)

        :param idx: index name
        :param ts: timestamp from (updated_ts)
        :param force: force index
        :param silent: silent mode
        """
        self.tmp_idx = idx  # store tmp index name (for confirmation)
        if not force:
            content = trans('idx.confirm.db.content') + "\n" + trans('idx.token.warn')
            self.window.ui.dialogs.confirm(
                type='idx.index.db.all',
                id=ts,
                msg=content,
            )
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
        self.window.controller.idx.on_idx_start()  # on start

    def index_path(
            self,
            path: str,
            idx: str = "base",
            replace: bool = None,
            recursive: bool = None
    ):
        """
        Index all files in path (threaded)

        :param path: path to file or directory
        :param idx: index name
        :param replace: replace index
        :param recursive: recursive indexing
        :param silent: silent mode
        """
        self.window.update_status(trans('idx.status.indexing'))
        worker = IndexWorker()
        worker.window = self.window
        worker.content = path
        worker.idx = idx
        worker.type = "file"
        worker.replace = replace
        worker.recursive = recursive
        worker.signals.finished.connect(self.handle_finished_file)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)
        self.window.controller.idx.on_idx_start()  # on start

    def index_paths(
            self,
            paths: list,
            idx: str = "base",
            replace: bool = None,
            recursive: bool = None
    ):
        """
        Index all files in path (threaded)

        :param paths: paths to files or directories
        :param idx: index name
        :param replace: replace index
        :param recursive: recursive indexing
        """
        self.window.update_status(trans('idx.status.indexing'))
        worker = IndexWorker()
        worker.window = self.window
        worker.content = paths
        worker.idx = idx
        worker.type = "files"
        worker.replace = replace
        worker.recursive = recursive
        worker.silent = False
        worker.signals.finished.connect(self.handle_finished_file)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)
        self.window.controller.idx.on_idx_start()  # on start

    def index_all_files(
            self,
            idx: str,
            force: bool = False
    ):
        """
        Index all files in data directory (threaded)

        :param idx: index name
        :param force: force index
        """
        self.tmp_idx = idx  # store tmp index name (for confirmation)
        path = self.window.core.config.get_user_dir('data')
        if not force:
            content = trans('idx.confirm.files.content').replace('{dir}', path) \
                      + "\n" + trans('idx.token.warn')
            self.window.ui.dialogs.confirm(
                type='idx.index.files.all',
                id=idx,
                msg=content,
            )
            return
        self.index_path(path, idx)

    def index_file_confirm(self, path: str):
        """
        Index file (force execute)

        :param path: path to file or directory
        """
        # get stored index name
        if self.tmp_idx is None:
            return
        self.window.update_status(trans('idx.status.indexing'))
        self.index_path(path, self.tmp_idx)

    def index_file(
            self,
            path: str,
            idx: str = "base",
            force: bool = False
    ):
        """
        Index file or directory (threaded)

        :param path: path to file or directory
        :param idx: index name
        :param force: force index
        """
        self.tmp_idx = idx  # store tmp index name (for confirmation)
        if not force:
            content = trans('idx.confirm.file.content').replace('{dir}', path) \
                      + "\n" + trans('idx.token.warn')
            self.window.ui.dialogs.confirm(
                type='idx.index.file',
                id=path,
                msg=content,
            )
            return
        self.index_path(path, idx)

    def index_file_remove_confirm(self, path: str):
        """
        Remove file (force execute)

        :param path: path to index
        """
        # get stored index name
        if self.tmp_idx is None:
            return

        self.window.core.idx.remove_file(
            self.tmp_idx,
            path,
        )
        self.window.update_status(trans('status.deleted') + ": " + path)
        self.tmp_idx = None
        self.update_explorer()  # update file status in explorer

    def index_file_remove(
            self,
            path: str,
            idx: str = "base",
            force: bool = False
    ):
        """
        Remove file or directory from index

        :param path: path to file or directory
        :param idx: index name
        :param force: force index
        """
        self.tmp_idx = idx  # store tmp index name (for confirmation)
        if not force:
            content = trans('idx.confirm.file.remove.content').replace('{dir}', path)
            self.window.ui.dialogs.confirm(
                type='idx.index.file.remove',
                id=path,
                msg=content,
            )
            return
        self.index_file_remove_confirm(path)
        self.window.tools.get("indexer").refresh()

    def index_web(
            self,
            idx: str,
            loader: str,
            params: dict,
            config: dict,
            replace: bool = True,
    ):
        """
        Index web content (threaded)

        :param idx: index name
        :param loader: loader name
        :param params: loader params
        :param config: loader config
        :param replace: replace index
        """
        worker = IndexWorker()
        worker.window = self.window
        worker.content = None
        worker.loader = loader
        worker.params = params
        worker.config = config
        worker.replace = replace
        worker.silent = False
        worker.idx = idx
        worker.type = "web"
        worker.signals.finished.connect(self.handle_finished_web)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)
        self.window.controller.idx.on_idx_start()  # on start

    def index_ctx_meta_remove(
            self,
            idx: str,
            meta_id: int,
            force: bool = False
    ):
        """
        Remove ctx meta from index

        :param idx: index name
        :param meta_id: meta id
        :param force: force index
        """
        if not force:
            self.tmp_idx = idx  # store tmp index name (for confirmation)
            content = "Remove context data from index?"
            self.window.ui.dialogs.confirm(
                type='idx.index.ctx.remove',
                id=meta_id,
                msg=content,
            )
            return

        store = self.window.core.idx.get_current_store()
        if self.window.core.ctx.idx.remove_meta_from_indexed(store, meta_id, self.tmp_idx):
            self.window.update_status(trans('status.deleted') + ": " + str(meta_id))
            self.window.controller.ctx.update()  # update ctx list

        self.window.tools.get("indexer").refresh()

    def clear_by_idx(self, idx: int):
        """
        Clear index by list idx

        :param idx: on list idx
        """
        idx_name = self.window.core.idx.get_by_idx(idx)
        self.clear(idx_name)

    def truncate_by_idx(self, idx: int):
        """
        Truncate index by list idx

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
            content = trans('idx.confirm.clear.content').replace('{dir}', path)
            self.window.ui.dialogs.confirm(
                type='idx.clear',
                id=idx,
                msg=content,
            )
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

        self.window.tools.get("indexer").refresh()

    def truncate(self, idx: str, force: bool = False):
        """
        Truncate index data

        :param idx: index name
        :param force: force clear
        """
        path = os.path.join(self.window.core.config.get_user_dir('idx'), idx)
        if not force:
            content = trans('idx.confirm.clear.content').replace('{dir}', path)
            self.window.ui.dialogs.confirm(
                type='idx.truncate',
                id=idx,
                msg=content,
            )
            return

        # remove current index
        self.window.update_status(trans('idx.status.truncating'))
        QApplication.processEvents()  # update UI to show status

        try:
            result = self.window.core.idx.remove_index(
                idx,
                truncate=True,
            )
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

        self.window.tools.get("indexer").refresh()

    @Slot(object)
    def handle_error(self, err: any):
        """
        Handle thread error signal

        :param err: error message
        """
        self.window.ui.dialogs.alert(err)
        self.window.update_status(str(err))
        self.window.core.debug.log(err)
        print(err)
        self.window.tools.get("indexer").refresh()
        self.window.controller.idx.on_idx_error()  # on error

    @Slot(str, object, object)
    def handle_finished_db_current(
            self,
            idx: str,
            num: int,
            errors: list,
            silent: bool = False
    ):
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
            self.window.core.config.set(
                'llama.idx.db.last',
                int(datetime.datetime.now().timestamp())
            )
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

        self.window.tools.get("indexer").refresh()
        self.window.controller.idx.on_idx_end()  # on end

    @Slot(str, object, object, bool)
    def handle_finished_db_meta(
            self,
            idx: str,
            num: int,
            errors: list,
            silent: bool = False
    ):
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

        self.window.tools.get("indexer").refresh()
        self.window.controller.idx.on_idx_end()  # on end

    @Slot(str, object, object, bool)
    def handle_finished_file(
            self,
            idx: str,
            files: dict,
            errors: list,
            silent: bool = False
    ):
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

        self.window.tools.get("indexer").on_finish_files()
        self.window.tools.get("indexer").refresh()
        self.window.controller.idx.on_idx_end()  # on end

    @Slot(str, object, object, bool)
    def handle_finished_web(
            self,
            idx: str,
            num: int,
            errors: list,
            silent: bool = False
    ):
        """
        Handle indexing finished signal

        :param idx: index name
        :param num: number of indexed records
        :param errors: errors
        :param silent: silent mode (no msg and status update)
        """
        if num > 0:
            msg = trans('idx.status.success') + f" {num}"
            if not silent:
                self.window.update_status(msg)
                self.window.ui.dialogs.alert(msg)
        else:
            self.window.update_status(trans('idx.status.empty'))

        if len(errors) > 0:
            self.window.ui.dialogs.alert("\n".join(errors))

        self.window.tools.get("indexer").on_finish_web()
        self.window.tools.get("indexer").refresh()
        self.window.controller.idx.on_idx_end()  # on end