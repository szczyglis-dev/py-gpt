#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class Importer(QObject):
    def __init__(self, window=None):
        """
        Importer core (Google File Search)

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
        if mode == "import_files":
            self.window.controller.remote_store.google.batch.handle_imported_files_failed(err)
        elif mode == "truncate_files":
            self.window.controller.remote_store.google.batch.handle_truncated_files_failed(err)
        elif mode == "upload_files":
            self.window.controller.remote_store.google.batch.handle_uploaded_files_failed(err)
        elif mode in "vector_stores":
            self.window.controller.remote_store.google.batch.handle_imported_stores_failed(err)
        elif mode in "truncate_vector_stores":
            self.window.controller.remote_store.google.batch.handle_truncated_stores_failed(err)
        elif mode in "refresh_vector_stores":
            self.window.controller.remote_store.google.batch.handle_refreshed_stores_failed(err)

    @Slot(str, str, int)
    def handle_finished(self, mode: str, store_id: str = None, num: int = 0):
        """
        Handle thread finished signal

        :param mode: mode
        :param store_id: store ID
        :param num: number of affected items
        """
        if mode == "import_files":
            self.window.controller.remote_store.google.batch.handle_imported_files(num)
        elif mode == "truncate_files":
            self.window.controller.remote_store.google.batch.handle_truncated_files(store_id, num)
        elif mode == "upload_files":
            self.window.controller.remote_store.google.batch.handle_uploaded_files(num)
        elif mode == "vector_stores":
            self.window.controller.remote_store.google.batch.handle_imported_stores(num)
        elif mode == "truncate_vector_stores":
            self.window.controller.remote_store.google.batch.handle_truncated_stores(num)
        elif mode == "refresh_vector_stores":
            self.window.controller.remote_store.google.batch.handle_refreshed_stores(num)

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
        """Import assistants (kept for parity; no-op for Google if unused)"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "assistants"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def import_vector_stores(self):
        """Import File Search stores"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "vector_stores"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def truncate_vector_stores(self):
        """Truncate File Search stores"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "truncate_vector_stores"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def truncate_files(self, store_id: str = None):
        """
        Truncate documents

        :param store_id: store name ('fileSearchStores/...').
        """
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "truncate_files"
        self.worker.store_id = store_id
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def upload_files(self, store_id: str, files: list = None):
        """
        Upload files

        :param store_id: store name ('fileSearchStores/...').
        :param files: list of file paths
        """
        print("Uploading files: {}".format(files))
        print("Store ID: {}".format(store_id))
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "upload_files"
        self.worker.store_id = store_id
        self.worker.files = files or []
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def refresh_vector_stores(self):
        """Refresh File Search stores"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "refresh_vector_stores"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def import_files(self, store_id: str = None):
        """
        Import File Search documents

        :param store_id: store name ('fileSearchStores/...').
        """
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "import_files"
        self.worker.store_id = store_id
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
    status = Signal(str, str)            # mode, message
    finished = Signal(str, str, int)     # mode, store_id, num
    error = Signal(str, object)          # mode, error
    log = Signal(str, str)               # mode, message


class ImportWorker(QRunnable):
    """Import worker (Google)"""
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
            if self.mode == "vector_stores":
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
        finally:
            self.cleanup()

    def import_assistants(self, silent: bool = False) -> bool:
        """
        Import assistants (not used for Google by default; kept for parity)

        :param silent: silent mode
        """
        try:
            if not silent:
                self.signals.finished.emit("assistants", self.store_id, 0)
            return True
        except Exception as e:
            self.signals.error.emit("assistants", e)
            return False

    def import_vector_stores(self, silent: bool = False) -> bool:
        """
        Import File Search stores

        :param silent: silent mode (no signals emit)
        """
        try:
            self.log("Importing File Search stores...")
            self.window.core.remote_store.google.clear()
            items = {}
            self.window.core.api.google.store.import_stores(items, callback=self.callback)
            self.window.core.remote_store.google.import_items(items)
            if not silent:
                self.signals.finished.emit("vector_stores", self.store_id, len(items))
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("vector_stores", e)
            return False

    def truncate_vector_stores(self, silent: bool = False) -> bool:
        """
        Truncate all File Search stores in API

        :param silent: silent mode
        """
        try:
            self.log("Truncating stores...")
            num = self.window.core.api.google.store.remove_all(callback=self.callback)
            self.window.core.remote_store.google.items = {}
            self.window.core.remote_store.google.save()
            if not silent:
                self.signals.finished.emit("truncate_vector_stores", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("truncate_vector_stores", e)
            return False

    def refresh_vector_stores(self, silent: bool = False) -> bool:
        """
        Refresh all File Search stores in API

        :param silent: silent mode
        """
        try:
            self.log("Refreshing stores...")
            num = 0
            stores = self.window.core.remote_store.google.items
            for id in stores:
                store = stores[id]
                try:
                    self.window.controller.remote_store.google.refresh_store(store, update=False)
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
        Truncate documents in API

        :param silent: silent mode
        """
        try:
            if self.store_id is None:
                self.log("Truncating all documents in all stores...")
                self.window.core.remote_store.google.files.truncate()  # clear all locally and remote
                num = self.window.core.api.google.store.remove_from_stores()
            else:
                self.log("Truncating documents for store: {}".format(self.store_id))
                self.window.core.remote_store.google.files.truncate(self.store_id)
                num = self.window.core.api.google.store.remove_from_store(self.store_id)
            if not silent:
                self.signals.finished.emit("truncate_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("truncate_files", e)
            return False

    def upload_files(self, silent: bool = False) -> bool:
        """
        Upload files directly to a File Search store (creates Documents)

        :param silent: silent mode
        """
        num = 0
        try:
            self.log("Uploading files to File Search store...")
            for file in self.files:
                try:
                    doc = self.window.core.api.google.store.upload_to_store(self.store_id, file)
                    if doc is not None:
                        self.window.core.remote_store.google.files.insert(self.store_id, doc)
                        msg = "Uploaded file: {}/{}".format((num + 1), len(self.files))
                        self.signals.status.emit("upload_files", msg)
                        self.log(msg)
                        num += 1
                    else:
                        self.signals.status.emit("upload_files", "Failed to upload file: {}".format(os.path.basename(file)))
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
        Import documents from API

        :param silent: silent mode
        """
        try:
            if self.store_id is None:
                self.log("Importing all documents...")
                self.window.core.remote_store.google.files.truncate_local()  # clear local DB (all)
                num = self.window.core.api.google.store.import_stores_files(self.callback)  # import all
            else:
                self.log("Importing documents for store: {}".format(self.store_id))
                self.window.core.remote_store.google.files.truncate_local(self.store_id)
                items = self.window.core.api.google.store.import_store_files(self.store_id, [], callback=self.callback)
                num = len(items)
            if not silent:
                self.signals.finished.emit("import_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("import_files", e)
            return False

    def callback(self, msg: str):
        """Log callback"""
        self.log(msg)

    def log(self, msg: str):
        """Log message"""
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