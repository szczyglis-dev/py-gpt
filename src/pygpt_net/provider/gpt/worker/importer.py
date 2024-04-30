#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 16:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class Importer:
    def __init__(self, window=None):
        """
        Importer core

        :param window: Window instance
        """
        self.window = window

    @Slot(str, object)
    def handle_error(self, mode: str, err: any):
        """
        Handle thread error signal

        :param mode: mode
        :param err: error message
        """
        if mode == "assistants":
            self.window.controller.assistant.batch.handle_imported_assistants_failed(err)
        elif mode == "import_files":
            self.window.controller.assistant.batch.handle_imported_files_failed(err)
        elif mode == "truncate_files":
            self.window.controller.assistant.batch.handle_truncated_files_failed(err)
        elif mode == "upload_files":
            self.window.controller.assistant.batch.handle_uploaded_files_failed(err)
        elif mode in "vector_stores":
            self.window.controller.assistant.batch.handle_imported_stores_failed(err)
        elif mode in "truncate_vector_stores":
            self.window.controller.assistant.batch.handle_truncated_stores_failed(err)
        elif mode in "refresh_vector_stores":
            self.window.controller.assistant.batch.handle_refreshed_stores_failed(err)

    @Slot(str, str, int)
    def handle_finished(self, mode: str, store_id: str = None, num: int = 0):
        """
        Handle thread finished signal

        :param mode: mode
        :param store_id: store ID
        :param num: number of affected items
        """
        if mode == "assistants":
            self.window.controller.assistant.batch.handle_imported_assistants(num)
        elif mode == "import_files":
            self.window.controller.assistant.batch.handle_imported_files(num)
        elif mode == "truncate_files":
            self.window.controller.assistant.batch.handle_truncated_files(store_id, num)
        elif mode == "upload_files":
            self.window.controller.assistant.batch.handle_uploaded_files(num)
        elif mode == "vector_stores":
            self.window.controller.assistant.batch.handle_imported_stores(num)
        elif mode == "truncate_vector_stores":
            self.window.controller.assistant.batch.handle_truncated_stores(num)
        elif mode == "refresh_vector_stores":
            self.window.controller.assistant.batch.handle_refreshed_stores(num)

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
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "assistants"
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def import_vector_stores(self):
        """Import vector stores"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "vector_stores"
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def truncate_vector_stores(self):
        """Truncate vector stores"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "truncate_vector_stores"
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def truncate_files(self, store_id: str = None):
        """
        Truncate files

        :param store_id: store ID
        """
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "truncate_files"
        worker.store_id = store_id
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def upload_files(self, store_id: str, files: list = None):
        """
        Upload files

        :param store_id: store ID
        :param files: files
        """
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "upload_files"
        worker.store_id = store_id
        worker.files = files
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def refresh_vector_stores(self):
        """Refresh vector stores"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "refresh_vector_stores"
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def import_files(self, store_id: str = None):
        """
        Import assistant files

        :param store_id: store ID
        """
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "import_files"
        worker.store_id = store_id
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

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
        super(ImportWorker, self).__init__()
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
            elif self.mode == "vector_stores":
                if self.import_vector_stores():
                    self.import_files()
            elif self.mode == "truncate_vector_stores":
                self.truncate_vector_stores()
            elif self.mode == "refresh_vector_stores":
                self.refresh_vector_stores()
            elif self.mode == "truncate_files":
                self.truncate_files()
            elif self.mode == "import_files":
                self.import_files()
            elif self.mode == "upload_files":
                self.upload_files()
        except Exception as e:
            self.signals.error.emit(self.mode, e)

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
            self.window.core.gpt.assistants.import_all(items, callback=self.callback)
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

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            self.log("Importing vector stores...")
            self.window.core.assistants.store.clear()
            items = {}
            self.window.core.gpt.store.import_stores(items, callback=self.callback)
            self.window.core.assistants.store.import_items(items)
            if not silent:
                self.signals.finished.emit("vector_stores", self.store_id, len(items))
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("vector_stores", e)
            return False

    def truncate_vector_stores(self, silent: bool = False) -> bool:
        """
        Truncate all vector stores in API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            self.log("Truncating stores...")
            num = self.window.core.gpt.store.remove_all(callback=self.callback)
            self.window.core.assistants.store.items = {}
            self.window.core.assistants.store.save()
            if not silent:
                self.signals.finished.emit("truncate_vector_stores", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("truncate_vector_stores", e)
            return False

    def refresh_vector_stores(self, silent: bool = False) -> bool:
        """
        Refresh all vector stores in API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            self.log("Refreshing stores...")
            num = 0
            stores = self.window.core.assistants.store.items
            for id in stores:
                store = stores[id]
                try:
                    self.window.controller.assistant.store.refresh_store(store, update=False)
                    num += 1
                except Exception as e:
                    self.log("Failed to refresh store: {}".format(id))
                    self.window.core.debug.log(e)
            if not silent:
                self.signals.finished.emit("refresh_vector_stores", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("refresh_vector_stores", e)
            return False

    def truncate_files(self, silent: bool = False) -> bool:
        """
        Truncate files in API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            # if empty store_id, truncate all files, otherwise truncate only store files
            if self.store_id is None:
                self.log("Truncating all files...")
                self.window.core.assistants.files.truncate() # clear all files
                # remove all files in API
                num = self.window.core.gpt.store.remove_files(callback=self.callback)
            else:
                self.log("Truncating files for store: {}".format(self.store_id))
                self.window.core.assistants.files.truncate(self.store_id)  # clear store files, remove from stores / DB
                # remove store files in API
                num = self.window.core.gpt.store.remove_store_files(
                    self.store_id,
                    callback=self.callback,
                )
            if not silent:
                self.signals.finished.emit("truncate_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("truncate_files", e)
            return False

    def upload_files(self, silent: bool = False) -> bool:
        """
        Upload files to API

        :param silent: silent mode (no signals)
        :return: result
        """
        num = 0
        try:
            self.log("Uploading files...")
            for file in self.files:
                try:
                    file_id = self.window.core.gpt.store.upload(file)
                    if file_id is not None:
                        stored_file = self.window.core.gpt.store.add_file(
                            self.store_id,
                            file_id,
                        )
                        if stored_file is not None:
                            data = self.window.core.gpt.store.get_file(file_id)
                            self.window.core.assistants.files.insert(self.store_id, data)  # insert to DB
                            msg = "Uploaded file: {}/{}".format((num + 1), len(self.files))
                            self.signals.status.emit("upload_files", msg)
                            self.log(msg)
                            num = num + 1
                except Exception as e:
                    self.window.core.debug.log(e)
                    self.signals.status.emit("upload_files", "Failed to upload file: {}".format(os.path.basename(file)))
            if not silent:
                self.signals.finished.emit("upload_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("upload_files", e)
            return False

    def import_files(self, silent: bool = False) -> bool:
        """
        Import assistant files from API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            if self.store_id is None:
                self.log("Importing all files...")
                self.window.core.assistants.files.truncate_local()  # clear local DB (all)
                num = self.window.core.gpt.store.import_stores_files(self.callback)  # import all files
            else:
                self.log("Importing files for store: {}".format(self.store_id))
                self.window.core.assistants.files.truncate_local(self.store_id)  # clear local DB (all)
                items = self.window.core.gpt.store.import_store_files(
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
