#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.11 04:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.utils import trans


class Idx:
    def __init__(self, window=None):
        """
        Indexes controller

        :param window: Window instance
        """
        self.window = window
        self.current_idx = "base"

    def setup(self):
        """
        Setup indexer
        """
        self.window.core.idx.load()
        self.update_explorer()

    def update_explorer(self):
        """Update file explorer view"""
        index_data = self.window.core.idx.get_idx_data(self.current_idx)
        self.window.ui.nodes['output_files'].model.update_idx_status(index_data)

    def index_path(self, path: str):
        """
        Index all files in path (threaded)
        """
        self.window.update_status(trans('idx.status.indexing'))

        worker = IndexWorker()
        worker.window = self.window
        worker.path = path
        worker.idx = self.current_idx
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def index_all(self, force: bool = False):
        """
        Index all files in output directory

        :param force: force index
        """
        path = os.path.join(self.window.core.config.path, 'output')
        if not force:
            self.window.ui.dialogs.confirm('idx.index_all', -1, trans('idx.confirm.content').
                                           replace('{dir}', path))
            return
        self.index_path(path)

    def clear(self, force: bool = False):
        """
        Re-index all files in output directory (remove old index)

        :param force: force index
        """
        path = os.path.join(self.window.core.config.path, 'output')
        if not force:
            self.window.ui.dialogs.confirm('idx.reindex_all', -1, trans('idx.confirm.clear.content').
                                           replace('{dir}', path))
            return

        # remove current index
        self.window.update_status(trans('idx.status.truncating'))
        QApplication.processEvents()  # update UI to show status

        try:
            result = self.window.core.idx.remove_index(self.current_idx)
            if result:
                self.window.core.idx.clear(self.current_idx)
                self.window.update_status(trans('idx.status.truncate.success'))
                self.update_explorer()  # update file explorer view
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
        print(e)

    @Slot(object, object)
    def handle_finished(self, files: dict, errors: list):
        """
        Handle indexing finished signal

        :param files: indexed files
        :param errors: errors
        """
        num = len(files)
        if num > 0:
            self.window.core.idx.append(self.current_idx, files)
            self.update_explorer()  # update file explorer view
            self.window.update_status(trans('idx.status.success') + f" {num}")
        else:
            self.window.update_status(trans('idx.status.empty'))

        if len(errors) > 0:
            self.window.ui.dialogs.alert("\n".join(errors))


class IndexWorkerSignals(QObject):
    finished = Signal(object, object)  # files, errors
    error = Signal(object)


class IndexWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(IndexWorker, self).__init__()
        self.signals = IndexWorkerSignals()
        self.window = None
        self.path = None
        self.idx = None

    @Slot()
    def run(self):
        """Indexer thread"""
        try:
            files, errors = self.window.core.idx.index(self.idx, self.path)
            self.signals.finished.emit(files, errors)
        except Exception as e:
            self.signals.error.emit(e)
