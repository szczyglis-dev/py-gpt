#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 12:30:00                  #
# ================================================== #

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.core.types import MODE_ASSISTANT


class InputWorkerSignals(QObject):
    success = Signal(int, str)
    error = Signal(int, object)


class InputWorker(QRunnable):
    """Prepare a manual user send without blocking the UI thread."""

    def __init__(self, window, request_id: int, mode: str, text: str, meta):
        super().__init__()
        self.signals = InputWorkerSignals()
        self.window = window
        self.request_id = request_id
        self.mode = mode
        self.text = text
        self.meta = meta
        self.cancelled = False

    def cancel(self):
        """Prevent this worker from advancing the send pipeline."""
        self.cancelled = True

    @Slot()
    def run(self):
        """Resolve mentions and process attachments, then continue the send."""
        try:
            if self.cancelled:
                return

            text = self.window.controller.chat.input._resolve_history_mentions(self.text)
            if self.cancelled:
                return

            attachment = self.window.controller.chat.attachment
            if self.mode != MODE_ASSISTANT and attachment.has(self.mode):
                attachment.upload(self.meta, self.mode, text)
            if self.cancelled:
                return

            safe_emit(self.signals, "success", self.request_id, text)
        except Exception as e:
            if not self.cancelled:
                safe_emit(self.signals, "error", self.request_id, e)
            self.window.core.debug.error(e)
        finally:
            self.cleanup()

    def cleanup(self):
        """Release Qt signal resources after execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass
