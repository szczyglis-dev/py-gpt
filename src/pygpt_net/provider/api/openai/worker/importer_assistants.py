#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 17:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class Importer(QObject):
    def __init__(self, window=None):
        """
        Importer core

        :param window: Window instance
        """
        super(Importer, self).__init__()
        self.window = window
        self.worker = None

    @Slot(str, object)
    def handle_error(self, mode: str, err: any):
        """
        Handle thread error signal

        :param mode: mode
        :param err: error message
        """
        batch = self.window.controller.remote_store.batch
        if mode == "assistants":
            self.window.controller.assistant.batch.handle_imported_assistants_failed(err)

    @Slot(str, str, int)
    def handle_finished(self, mode: str, store_id: str = None, num: int = 0):
        """
        Handle thread finished signal

        :param mode: mode
        :param store_id: store ID
        :param num: number of affected items
        """
        batch = self.window.controller.remote_store.batch
        if mode == "assistants":
            self.window.controller.assistant.batch.handle_imported_assistants(num)

    @Slot(str, str)
    def handle_status(self, mode: str, msg: str):
        """
        Handle thread status change signal

        :param mode: mode
        :param msg: message
        """
        self.window.controller.assistant.batch.handle_status_change(mode, msg)

    @Slot(str, str)
    def handle_log(self, mode: str, msg: str):
        """
        Handle thread log message signal

        :param mode: mode
        :param msg: message
        """
        self.window.controller.assistant.threads.log(mode + ": " + msg)

    def import_assistants(self):
        """Import assistants"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "assistants"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def connect_signals(self, worker):
        """
        Connect signals

        :param worker: worker instance
        """
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        worker.signals.status.connect(self.handle_status)
        worker.signals.log.connect(self.handle_log)


class ImportWorkerSignals(QObject):
    """Import worker signals"""
    status = Signal(str, str)  # mode, message
    finished = Signal(str, str, int)  # mode, store_id, num
    error = Signal(str, object)  # mode, error
    log = Signal(str, str)  # mode, message


class ImportWorker(QRunnable):
    """Import worker"""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ImportWorkerSignals()
        self.window = None
        self.mode = "assistants"
        self.assistant = None
        self.store_id = None
        self.files = []

    @Slot()
    def run(self):
        """Importer thread"""
        try:
            # import data
            if self.mode == "assistants":
                self.import_assistants()

        except Exception as e:
            self.signals.error.emit(self.mode, e)

        finally:
            self.cleanup()

    def import_assistants(self, silent: bool = False) -> bool:
        """
        Import assistants from API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            # import assistants
            self.log("Importing assistants...")
            self.window.core.assistants.clear()
            items = self.window.core.assistants.get_all()
            self.window.core.api.openai.assistants.import_all(items, callback=self.callback)
            self.window.core.assistants.items = items
            self.window.core.assistants.save()

            # import vector stores
            self.import_vector_stores(True)

            # import files
            self.import_files(True)

            if not silent:
                self.signals.finished.emit("assistants", self.store_id, len(items))
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("assistants", e)
            return False

    def import_vector_stores(self, silent: bool = False) -> bool:
        """
        Import vector stores from API

        :param silent: silent mode (no signals emit)
        :return: result
        """
        try:
            self.log("Importing vector stores...")
            self.window.core.remote_store.openai.clear()
            items = {}
            self.window.core.api.openai.store.import_stores(items, callback=self.callback)
            self.window.core.remote_store.openai.import_items(items)
            if not silent:
                self.signals.finished.emit("vector_stores", self.store_id, len(items))
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("vector_stores", e)
            return False

    def import_files(self, silent: bool = False) -> bool:
        """
        Import assistant files from API

        :param silent: silent mode (no signals emit)
        :return: result
        """
        try:
            if self.store_id is None:
                self.log("Importing all files...")
                self.window.core.remote_store.openai.files.truncate_local()  # clear local DB (all)
                num = self.window.core.api.openai.store.import_stores_files(self.callback)  # import all files
            else:
                self.log("Importing files for store: {}".format(self.store_id))
                self.window.core.remote_store.openai.files.truncate_local(self.store_id)  # clear local DB (all)
                items = self.window.core.api.openai.store.import_store_files(
                    self.store_id,
                    [],
                    callback=self.callback,
                )  # import store files
                num = len(items)
            if not silent:
                self.signals.finished.emit("import_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("import_files", e)
        return False

    def callback(self, msg: str):
        """
        Log callback

        :param msg: message
        """
        self.log(msg)

    def log(self, msg: str):
        """
        Log message

        :param msg: message
        """
        self.signals.log.emit(self.mode, msg)

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass
