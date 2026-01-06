#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 06:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class Importer(QObject):
    def __init__(self, window=None):
        """
        Importer core (xAI Collections)

        :param window: Window instance
        """
        super(Importer, self).__init__()
        self.window = window
        self.worker = None

    @Slot(str, object)
    def handle_error(self, mode: str, err: any):
        batch = self.window.controller.remote_store.batch
        if mode == "import_files":
            batch.handle_imported_files_failed(err)
        elif mode == "truncate_files":
            batch.handle_truncated_files_failed(err)
        elif mode == "upload_files":
            batch.handle_uploaded_files_failed(err)
        elif mode in "vector_stores":
            batch.handle_imported_stores_failed(err)
        elif mode in "truncate_vector_stores":
            batch.handle_truncated_stores_failed(err)
        elif mode in "refresh_vector_stores":
            batch.handle_refreshed_stores_failed(err)

    @Slot(str, str, int)
    def handle_finished(self, mode: str, store_id: str = None, num: int = 0):
        batch = self.window.controller.remote_store.batch
        if mode == "import_files":
            batch.handle_imported_files(num)
        elif mode == "truncate_files":
            batch.handle_truncated_files(store_id, num)
        elif mode == "upload_files":
            batch.handle_uploaded_files(num)
        elif mode == "vector_stores":
            batch.handle_imported_stores(num)
        elif mode == "truncate_vector_stores":
            batch.handle_truncated_stores(num)
        elif mode == "refresh_vector_stores":
            batch.handle_refreshed_stores(num)

    @Slot(str, str)
    def handle_status(self, mode: str, msg: str):
        self.window.controller.assistant.batch.handle_status_change(mode, msg)

    @Slot(str, str)
    def handle_log(self, mode: str, msg: str):
        self.window.controller.assistant.threads.log(mode + ": " + msg)

    # ---------- Vector stores (Collections) ----------

    def import_vector_stores(self):
        """Import collections"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "vector_stores"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def truncate_vector_stores(self):
        """Delete collections"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "truncate_vector_stores"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def refresh_vector_stores(self):
        """Refresh collections"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "refresh_vector_stores"
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    # ---------- Files (documents) ----------

    def truncate_files(self, store_id: str = None):
        """Remove documents from one/all collections"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "truncate_files"
        self.worker.store_id = store_id
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def upload_files(self, store_id: str, files: list = None):
        """Upload files to a collection"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "upload_files"
        self.worker.store_id = store_id
        self.worker.files = files or []
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def import_files(self, store_id: str = None):
        """Import documents from one/all collections"""
        self.worker = ImportWorker()
        self.worker.window = self.window
        self.worker.mode = "import_files"
        self.worker.store_id = store_id
        self.connect_signals(self.worker)
        self.window.threadpool.start(self.worker)

    def connect_signals(self, worker):
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        worker.signals.status.connect(self.handle_status)
        worker.signals.log.connect(self.handle_log)


class ImportWorkerSignals(QObject):
    status = Signal(str, str)            # mode, message
    finished = Signal(str, str, int)     # mode, store_id, num
    error = Signal(str, object)          # mode, error
    log = Signal(str, str)               # mode, message


class ImportWorker(QRunnable):
    """Import worker (xAI Collections)"""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = ImportWorkerSignals()
        self.window = None
        self.mode = "vector_stores"
        self.store_id = None
        self.files = []

    @Slot()
    def run(self):
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

    # ---------- Collections ----------

    def import_vector_stores(self, silent: bool = False) -> bool:
        try:
            self.log("Importing collections...")
            self.window.core.remote_store.xai.clear()
            items = {}
            self.window.core.api.xai.store.import_collections_collections(items, callback=self.callback)
            self.window.core.remote_store.xai.import_items(items)
            if not silent:
                self.signals.finished.emit("vector_stores", self.store_id, len(items))
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("vector_stores", e)
            return False

    def truncate_vector_stores(self, silent: bool = False) -> bool:
        try:
            self.log("Truncating collections...")
            num = self.window.core.api.xai.store.remove_all_collections_collections(callback=self.callback)
            self.window.core.remote_store.xai.items = {}
            self.window.core.remote_store.xai.save()
            if not silent:
                self.signals.finished.emit("truncate_vector_stores", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("truncate_vector_stores", e)
            return False

    def refresh_vector_stores(self, silent: bool = False) -> bool:
        try:
            self.log("Refreshing collections...")
            num = 0
            stores = self.window.core.remote_store.xai.items
            for id in list(stores.keys()):
                store = stores[id]
                try:
                    self.window.controller.remote_store.refresh_store(store, update=False, provider="xai")
                    num += 1
                except Exception as e:
                    self.log("Failed to refresh collection: {}".format(id))
                    self.window.core.debug.log(e)
            if not silent:
                self.signals.finished.emit("refresh_vector_stores", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("refresh_vector_stores", e)
            return False

    # ---------- Documents ----------

    def truncate_files(self, silent: bool = False) -> bool:
        try:
            if self.store_id is None:
                self.log("Truncating all collection documents...")
                self.window.core.remote_store.xai.files.truncate()  # clear all local + detach from all collections
                num = self.window.core.api.xai.store.remove_files(callback=self.callback)  # delete remote files
            else:
                self.log("Truncating documents for collection: {}".format(self.store_id))
                self.window.core.remote_store.xai.files.truncate(self.store_id)  # clear local + detach from this collection
                num = self.window.core.api.xai.store.remove_from_collection_collections(
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
        num = 0
        try:
            self.log("Uploading files to collection...")
            for path in self.files:
                try:
                    doc = self.window.core.api.xai.store.upload_to_collection_collections(self.store_id, path)
                    if doc is not None:
                        self.window.core.remote_store.xai.files.insert(self.store_id, doc.file_metadata)
                        num += 1
                        msg = "Uploaded file: {}/{}".format(num, len(self.files))
                        self.signals.status.emit("upload_files", msg)
                        self.log(msg)
                    else:
                        self.signals.status.emit("upload_files", "Failed to upload: {}".format(os.path.basename(path)))
                except Exception as e:
                    self.window.core.debug.log(e)
                    self.signals.status.emit("upload_files", "Failed to upload: {}".format(os.path.basename(path)))
            if not silent:
                self.signals.finished.emit("upload_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("upload_files", e)
            return False

    def import_files(self, silent: bool = False) -> bool:
        try:
            if self.store_id is None:
                self.log("Importing all collection documents...")
                self.window.core.remote_store.xai.files.truncate_local()  # clear local DB (all)
                num = self.window.core.api.xai.store.import_collections_files_collections(callback=self.callback)
            else:
                self.log("Importing documents for collection: {}".format(self.store_id))
                self.window.core.remote_store.xai.files.truncate_local(self.store_id)  # clear local DB (store)
                items = self.window.core.api.xai.store.import_collection_files_collections(
                    self.store_id,
                    [],
                    callback=self.callback,
                )
                num = len(items)
            if not silent:
                self.signals.finished.emit("import_files", self.store_id, num)
            return True
        except Exception as e:
            self.log("API error: {}".format(e))
            self.signals.error.emit("import_files", e)
            return False

    # ---------- Utils ----------

    def callback(self, msg: str):
        self.log(msg)

    def log(self, msg: str):
        self.signals.log.emit(self.mode, msg)

    def cleanup(self):
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass