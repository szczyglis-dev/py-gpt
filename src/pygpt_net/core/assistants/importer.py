#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.18 18:00:00                  #
# ================================================== #

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
            self.window.controller.assistant.handle_imported_assistants_failed(err)
        elif mode == "files":
            self.window.controller.assistant.files.handle_imported_files_failed(err)

    @Slot(str, int)
    def handle_finished(self, mode: str, num: int):
        """
        Handle thread finished signal

        :param mode: mode
        :param num: number of imported items
        """
        if mode == "assistants":
            self.window.controller.assistant.handle_imported_assistants(num)
        elif mode == "files":
            self.window.controller.assistant.files.handle_imported_files(num)

    def import_assistants(self):
        """Import assistants"""
        worker = ImportWorker()
        worker.window = self.window
        worker.mode = "assistants"
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
    finished = Signal(str, int)
    error = Signal(str, object)


class ImportWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(ImportWorker, self).__init__()
        self.signals = ImportWorkerSignals()
        self.window = None
        self.mode = "assistants"
        self.assistant = None

    @Slot()
    def run(self):
        """Importer thread"""
        try:
            # import data
            if self.mode == "assistants":
                self.import_assistants()
            elif self.mode == "files":
                self.import_files(self.assistant)

        except Exception as e:
            self.signals.error.emit(self.mode, e)

    def import_assistants(self, silent: bool = False) -> bool:
        """
        Import assistants from API

        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            items = self.window.core.assistants.get_all()
            self.window.core.gpt.assistants.import_api(items)
            self.window.core.assistants.items = items
            self.window.core.assistants.save()

            # import uploaded files
            for id in self.window.core.assistants.items:
                assistant = self.window.core.assistants.get_by_id(id)
                self.import_files(assistant, True)

            if not silent:
                self.signals.finished.emit("assistants", len(items))
            return True
        except Exception as e:
            self.signals.error.emit("assistants", e)
            return False

    def import_files(self, assistant: AssistantItem, silent: bool = False) -> bool:
        """
        Import assistant files from API

        :param assistant: assistant
        :param silent: silent mode (no signals)
        :return: result
        """
        try:
            files = self.window.core.gpt.assistants.file_list(assistant.id)
            self.window.core.assistants.import_files(assistant, files)
            self.window.core.assistants.save()

            if not silent:
                self.signals.finished.emit("files", len(files))
            return True
        except Exception as e:
            self.signals.error.emit("files", e)
        return False
