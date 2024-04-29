#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 12:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.item.assistant import AssistantItem


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
        elif mode == "files":
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

    @Slot(str, int)
    def handle_finished(self, mode: str, num: int):
        """
        Handle thread finished signal

        :param mode: mode
        :param num: number of imported items
        """
        if mode == "assistants":
            self.window.controller.assistant.batch.handle_imported_assistants(num)
        elif mode == "files":
            self.window.controller.assistant.batch.handle_imported_files(num)
        elif mode == "truncate_files":
            self.window.controller.assistant.batch.handle_truncated_files(num)
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

    def import_assistants(self):
        """Import assistants"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "assistants"
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def import_vector_stores(self):
        """Import vector stores"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "vector_stores"
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def truncate_vector_stores(self):
        """Truncate vector stores"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "truncate_vector_stores"
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def truncate_files(self):
        """Truncate files"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "truncate_files"
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def upload_files(self, store_id: str, files: list = None):
        """
        Upload files

        :param files: files
        :param store_id: store ID
        """
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "upload_files"
        worker.store_id = store_id
        worker.files = files
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        worker.signals.status.connect(self.handle_status)
        self.window.threadpool.start(worker)

    def refresh_vector_stores(self):
        """Refresh vector stores"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "refresh_vector_stores"
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def import_files(self, assistant: AssistantItem):
        """
        Import assistant files

        :param assistant: assistant
        """
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "files"
        worker.assistant = assistant
        worker.signals.finished.connect(self.handle_finished)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)


class ImportWorkerSignals(QObject):
    status = Signal(str, str)
    finished = Signal(str, int)
    error = Signal(str, object)


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
                self.import_vector_stores()
            elif self.mode == "truncate_vector_stores":
                self.truncate_vector_stores()
            elif self.mode == "refresh_vector_stores":
                self.refresh_vector_stores()
            elif self.mode == "truncate_files":
                self.truncate_files()
            elif self.mode == "files":
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
            print("Importing assistants...")
            self.window.core.assistants.clear()
            items = self.window.core.assistants.get_all()
            self.window.core.gpt.assistants.import_assistants(items)
            self.window.core.assistants.items = items
            self.window.core.assistants.save()

            # import vector stores
            self.import_vector_stores(True)

            # import files
            self.import_files(True)

            if not silent:
                self.signals.finished.emit("assistants", len(items))
            return True
        except Exception as e:
            self.signals.error.emit("assistants", e)
            return False

    def import_vector_stores(self, silent: bool = False) -> bool:
        """
        Import vector stores from API

        :return: result
        """
        try:
            print("Importing vector stores...")
            self.window.core.assistants.store.clear()
            items = self.window.core.assistants.store.get_all()
            self.window.core.gpt.assistants.import_vector_stores(items)
            self.window.core.assistants.store.import_items(items)
            if not silent:
                self.signals.finished.emit("vector_stores", len(items))
            return True
        except Exception as e:
            self.signals.error.emit("vector_stores", e)
            return False

    def truncate_vector_stores(self, silent: bool = False) -> bool:
        """
        Truncate all vector stores in API

        :return: result
        """
        try:
            print("Truncating stores...")
            num = self.window.core.gpt.assistants.vs_truncate_stores()
            self.window.core.assistants.store.items = {}
            self.window.core.assistants.store.save()
            if not silent:
                self.signals.finished.emit("truncate_vector_stores", num)
            return True
        except Exception as e:
            self.signals.error.emit("truncate_vector_stores", e)
            return False

    def refresh_vector_stores(self, silent: bool = False) -> bool:
        """
        Refresh all vector stores in API

        :return: result
        """
        try:
            print("Refreshing stores...")
            num = 0
            stores = self.window.core.assistants.store.items
            for id in stores:
                store = stores[id]
                self.window.controller.assistant.store.refresh_store(store, update=False)
                num += 1
            if not silent:
                self.signals.finished.emit("refresh_vector_stores", num)
            return True
        except Exception as e:
            self.signals.error.emit("refresh_vector_stores", e)
            return False

    def truncate_files(self, silent: bool = False) -> bool:
        """
        Truncate all files in API

        :return: result
        """
        try:
            print("Truncating files...")
            self.window.core.assistants.files.truncate()  # clear all files, remove from stores and DB
            num = self.window.core.gpt.assistants.files_truncate()  # remove files in API
            if not silent:
                self.signals.finished.emit("truncate_files", num)  # in DB (local) handled after
            return True
        except Exception as e:
            self.signals.error.emit("truncate_files", e)
            return False

    def upload_files(self, silent: bool = False) -> bool:
        """
        Upload files to API

        :return: result
        """
        num = 0
        try:
            print("Uploading files...")
            for file in self.files:
                try:
                    file_id = self.window.core.gpt.assistants.file_upload("", file)
                    if file_id is not None:
                        stored_file = self.window.core.gpt.assistants.vs_add_file(
                            self.store_id,
                            file_id,
                        )
                        if stored_file is not None:
                            data = self.window.core.gpt.assistants.file_info(file_id)
                            self.window.core.assistants.files.insert(self.store_id, data)  # insert to DB
                            self.signals.status.emit("upload_files",
                                                     "Uploaded file: {}/{}".format((num + 1), len(self.files)))
                            num = num + 1
                except Exception as e:
                    self.window.core.debug.log(e)
                    self.signals.status.emit("upload_files", "Failed to upload file: {}".format(os.path.basename(file)))
            if not silent:
                self.signals.finished.emit("upload_files", num)
            return True
        except Exception as e:
            self.signals.error.emit("upload_files", e)
            return False

    def import_files(self, silent: bool = False) -> bool:
        """
        Import assistant files from API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            print("Importing all files...")
            self.window.core.assistants.files.truncate_local()  # clear local DB
            num = self.window.core.gpt.assistants.vs_import_all_files()
            if not silent:
                self.signals.finished.emit("files", num)
            return True
        except Exception as e:
            self.signals.error.emit("files", e)
        return False
