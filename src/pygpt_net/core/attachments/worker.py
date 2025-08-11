#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 14:00:00                  #
# ================================================== #

from PySide6.QtCore import Signal, QObject, QRunnable, Slot


class WorkerSignals(QObject):
    success = Signal(str)
    error = Signal(object)


class AttachmentWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.meta = None
        self.mode = None
        self.prompt = ""

    @Slot()
    def run(self):
        """Index attachments"""
        try:
            self.window.controller.chat.attachment.upload(self.meta, self.mode, self.prompt)
            self.signals.success.emit(self.prompt)

        except Exception as e:
            if self.signals is not None:
                self.signals.error.emit(e)
            self.window.core.debug.error(e)
            print("Attachment indexing error", e)

        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass