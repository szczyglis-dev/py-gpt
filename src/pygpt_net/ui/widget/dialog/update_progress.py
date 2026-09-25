#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout

from pygpt_net.utils import sizeof_fmt, trans


class UpdateProgressDialog(QDialog):
    """Progress dialog for automatic application updates."""

    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self._active = False
        self._cancel = None
        self.setWindowTitle(trans("update.auto.title"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(460)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.details = QLabel("")
        self.details.setAlignment(Qt.AlignCenter)
        self.details.setWordWrap(True)

        self.cancel_button = QPushButton(trans("input.btn.cancel"))
        self.cancel_button.clicked.connect(self.request_cancel)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(10)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        layout.addWidget(self.details)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

    def start_update(self, cancel_callback, status: str):
        self._active = True
        self._cancel = cancel_callback
        self.cancel_button.setEnabled(True)
        self.status.setText(status)
        self.details.setText("")
        self.progress.setRange(0, 0)
        self.setModal(True)
        self.show()
        self.raise_()
        self.activateWindow()

    def set_progress(self, status: str, percent=None, received=0, total=0, speed=0.0, eta=None):
        self.status.setText(status or trans("update.auto.status.working"))
        if percent is None:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, int(percent))))

        parts = []
        if received:
            if total:
                parts.append(f"{sizeof_fmt(received)} / {sizeof_fmt(total)}")
            else:
                parts.append(sizeof_fmt(received))
        if speed:
            parts.append(f"{sizeof_fmt(speed)}/s")
        if eta is not None and eta >= 0:
            seconds = int(eta)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            if hours:
                eta_text = f"{hours:d}:{minutes:02d}:{seconds:02d}"
            else:
                eta_text = f"{minutes:02d}:{seconds:02d}"
            parts.append(f"{trans('update.auto.remaining')}: {eta_text}")
        self.details.setText("  •  ".join(parts))

    def finish_update(self):
        self._active = False
        self._cancel = None
        self.hide()

    def request_cancel(self):
        if not self._active:
            return
        self.cancel_button.setEnabled(False)
        if callable(self._cancel):
            self._cancel()

    def reject(self):
        if self._active:
            self.request_cancel()
            return
        super().reject()

    def closeEvent(self, event):
        if self._active and not getattr(self.window, "is_closing", False):
            self.request_cancel()
            event.ignore()
            return
        super().closeEvent(event)
