#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.15 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout

from pygpt_net.utils import trans


class LoaderDialog(QDialog):
    """Reusable indeterminate progress dialog with optional cancellation."""

    def __init__(self, window=None):
        super(LoaderDialog, self).__init__(window)
        self.window = window
        self._active = False
        self._finishing = False
        self._cancel_requested = False
        self._on_cancel = None
        self._on_finished = None

        self.setWindowTitle("PyGPT")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(320)

        self.message = QLabel("")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setWordWrap(True)

        # Same indeterminate progress mode used by the splash screen.
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)

        self.cancel_button = QPushButton("")
        self.cancel_button.clicked.connect(self.request_cancel)
        self.cancel_button.setVisible(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(12)
        layout.addWidget(self.message)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

        # QDialog.finished is deliberately used as the single completion
        # source so every close path invokes the public completion callback.
        self.finished.connect(self._handle_finished)

    def start(
            self,
            message: str = None,
            show_cancel: bool = False,
            on_cancel=None,
            on_finished=None,
            modal: bool = True,
    ):
        """
        Show the loader.

        :param message: text displayed above the progress bar
        :param show_cancel: show the optional Cancel button
        :param on_cancel: callback invoked once when cancellation is requested
        :param on_finished: callback invoked once with QDialog result code
        :param modal: block interaction with the parent window
        :return: this dialog instance
        """
        if self._active:
            self.finish()

        self._active = True
        self._finishing = False
        self._cancel_requested = False
        self._on_cancel = on_cancel
        self._on_finished = on_finished

        self.message.setText(message or trans('dialog.loader.wait'))
        self.cancel_button.setText(trans('input.btn.cancel'))
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(bool(show_cancel))
        self.setModal(bool(modal))

        self.adjustSize()
        self.show()
        self.raise_()
        self.activateWindow()
        return self

    def finish(self, result: int = QDialog.Accepted):
        """
        Finish and close the loader safely.

        :param result: QDialog result code forwarded to the finished callback
        """
        if not self._active and not self.isVisible():
            return
        self._finishing = True
        self.done(result)

    def request_cancel(self):
        """Request cancellation once without closing before the task ends."""
        if not self._active or not self.cancel_button.isVisible() or self._cancel_requested:
            return

        self._cancel_requested = True
        self.cancel_button.setEnabled(False)
        callback = self._on_cancel
        if callable(callback):
            try:
                callback()
            except Exception as e:
                self.window.core.debug.log(e)

    def reject(self):
        """Treat Escape as cancellation while an active loader is running."""
        if self._active and not self._finishing and not getattr(self.window, 'is_closing', False):
            self.request_cancel()
            return
        super().reject()

    def closeEvent(self, event):
        """Do not disappear while work is still running; request cancel instead."""
        if self._active and not self._finishing and not getattr(self.window, 'is_closing', False):
            self.request_cancel()
            event.ignore()
            return
        super().closeEvent(event)

    def _handle_finished(self, result: int):
        """Reset state and invoke the configured completion callback exactly once."""
        callback = self._on_finished
        was_active = self._active

        self._active = False
        self._finishing = False
        self._cancel_requested = False
        self._on_cancel = None
        self._on_finished = None
        self.cancel_button.setEnabled(True)

        if was_active and callable(callback):
            try:
                callback(result)
            except Exception as e:
                self.window.core.debug.log(e)
