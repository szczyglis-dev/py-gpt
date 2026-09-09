#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 13:30:00                  #
# ================================================== #

import os
from collections import deque

from PySide6.QtCore import QObject, QEvent, Qt, QRunnable, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import QMessageBox

from pygpt_net.utils import trans


# Show a confirmation before attaching more than this many files from a pasted
# directory. Set to 0 to disable the warning completely.
DIRECTORY_PASTE_WARNING_THRESHOLD = 10

# Directory enumeration and attachment insertion are chunked so a confirmed
# large paste does not monopolize the UI event loop.
DIRECTORY_SCAN_BATCH_SIZE = 50
DIRECTORY_PASTE_BATCH_SIZE = 10


class DirectoryCountSignals(QObject):
    finished = Signal(object, str, int, object)


class DirectoryCountWorker(QRunnable):
    """Count files recursively outside the UI thread."""

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.signals = DirectoryCountSignals()

    @Slot()
    def run(self):
        count = 0
        error = None
        try:
            for _, _, names in os.walk(self.path):
                count += len(names)
        except Exception as e:
            error = e
        self.signals.finished.emit(self, self.path, count, error)


class DirectoryEnumerateSignals(QObject):
    batch = Signal(object, object)
    finished = Signal(object, object)


class DirectoryEnumerateWorker(QRunnable):
    """Enumerate directory files in small batches outside the UI thread."""

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.signals = DirectoryEnumerateSignals()

    @Slot()
    def run(self):
        batch = []
        error = None
        try:
            for root, _, names in os.walk(self.path):
                for name in names:
                    batch.append(os.path.join(root, name))
                    if len(batch) >= DIRECTORY_SCAN_BATCH_SIZE:
                        self.signals.batch.emit(self, batch)
                        batch = []
            if batch:
                self.signals.batch.emit(self, batch)
        except Exception as e:
            error = e
        self.signals.finished.emit(self, error)


class DirectoryPasteHandler(QObject):
    """Safely scan, confirm and enqueue files from pasted directories."""

    def __init__(self, window, target_widget):
        super().__init__(target_widget)
        self.window = window
        self._target = target_widget
        self._workers = set()
        self._warning_queue = deque()
        self._warning_active = False
        self._file_queue = deque()

        self._add_timer = QTimer(self)
        self._add_timer.setInterval(0)
        self._add_timer.timeout.connect(self._process_file_queue)

    @staticmethod
    def _warning_threshold() -> int:
        try:
            return max(0, int(DIRECTORY_PASTE_WARNING_THRESHOLD))
        except (TypeError, ValueError):
            return 10

    def add_directory(self, path: str):
        """Start safe processing of a pasted directory."""
        if not path or not os.path.isdir(path):
            return

        # With warnings disabled there is no reason to make an extra counting pass.
        if self._warning_threshold() == 0:
            self._start_enumeration(path)
            return

        worker = DirectoryCountWorker(path)
        self._workers.add(worker)
        worker.signals.finished.connect(self._on_count_finished)
        QThreadPool.globalInstance().start(worker)

    @Slot(object, str, int, object)
    def _on_count_finished(self, worker, directory: str, count: int, error):
        self._workers.discard(worker)

        if error is not None:
            self._log_error(error)

        if count <= 0:
            return

        threshold = self._warning_threshold()
        if threshold > 0 and count > threshold:
            self._warning_queue.append((directory, count))
            self._show_next_warning()
        else:
            self._start_enumeration(directory)

    def _show_next_warning(self):
        if self._warning_active or not self._warning_queue:
            return

        self._warning_active = True
        directory, count = self._warning_queue.popleft()

        msg = trans("attachments.paste.directory.confirm").format(
            num=count,
            directory=directory,
        )

        dialog = QMessageBox(self._target)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle(trans("dialog.confirm.title"))
        dialog.setText(msg)

        btn_yes = dialog.addButton(trans("dialog.confirm.yes"), QMessageBox.YesRole)
        btn_no = dialog.addButton(trans("dialog.confirm.no"), QMessageBox.NoRole)
        dialog.setDefaultButton(btn_no)
        dialog.setEscapeButton(btn_no)
        dialog.exec()

        if dialog.clickedButton() is btn_yes:
            self._start_enumeration(directory)

        dialog.deleteLater()
        self._warning_active = False
        QTimer.singleShot(0, self._show_next_warning)

    def _start_enumeration(self, directory: str):
        worker = DirectoryEnumerateWorker(directory)
        self._workers.add(worker)
        worker.signals.batch.connect(self._on_files_batch)
        worker.signals.finished.connect(self._on_enumeration_finished)
        QThreadPool.globalInstance().start(worker)

    @Slot(object, object)
    def _on_files_batch(self, worker, files):
        if files:
            self._file_queue.extend(files)
            if not self._add_timer.isActive():
                self._add_timer.start()

    @Slot(object, object)
    def _on_enumeration_finished(self, worker, error):
        self._workers.discard(worker)
        if error is not None:
            self._log_error(error)

    def _process_file_queue(self):
        batch_size = max(1, int(DIRECTORY_PASTE_BATCH_SIZE))
        processed = 0

        while self._file_queue and processed < batch_size:
            path = self._file_queue.popleft()
            try:
                self.window.controller.attachment.from_clipboard_url(path, all=True)
            except Exception as e:
                self._log_error(e)
            processed += 1

        if not self._file_queue:
            self._add_timer.stop()

    def _log_error(self, error):
        try:
            self.window.core.debug.log(error)
        except Exception:
            pass


class AttachmentDropHandler(QObject):
    """
    Generic drag & drop handler for attaching files/images/urls/text.

    Policies:
    - SWALLOW_ALL: always consume the drop (e.g., attachments list).
    - INPUT_MIX  : for ChatInput; process attachments and:
        * swallow image payloads (no text insert),
        * allow default handling for non-image payloads so paths/text get inserted.
    """
    SWALLOW_ALL = 0
    INPUT_MIX = 1

    def __init__(self, window, target_widget, policy=SWALLOW_ALL):
        super().__init__(target_widget)
        self.window = window
        self._target = target_widget
        self._policy = policy

        # Accept drops on target and its viewport (important for QTextEdit/QAbstractScrollArea)
        self._enable_drops(self._target)
        vp = self._get_viewport(self._target)
        if vp is not None:
            self._enable_drops(vp)

        # Install filters on both
        self._target.installEventFilter(self)
        if vp is not None:
            vp.installEventFilter(self)

    def _enable_drops(self, w):
        try:
            w.setAcceptDrops(True)
        except Exception:
            pass

    def _get_viewport(self, w):
        try:
            vp = getattr(w, "viewport", None)
            if callable(vp):
                return vp()
            return None
        except Exception:
            return None

    def _mime_supported(self, md) -> bool:
        try:
            if md is None:
                return False
            return md.hasUrls() or md.hasImage() or md.hasText()
        except Exception:
            return False

    def _process_drop(self, md):
        """
        Route to ChatInput.handle_clipboard() to reuse existing attach pipeline.
        """
        try:
            chat_input = self.window.ui.nodes.get('input')
        except Exception:
            chat_input = None

        if chat_input is not None and hasattr(chat_input, 'handle_clipboard'):
            try:
                chat_input.handle_clipboard(md)
                return chat_input
            except Exception as e:
                try:
                    self.window.core.debug.log(e)
                except Exception:
                    pass
        return None

    def _allow_default_text_insert_for_non_image(self, md) -> bool:
        try:
            return not (md and md.hasImage())
        except Exception:
            return True

    def eventFilter(self, obj, event):
        # Only handle events coming to the target or its viewport
        if obj is not self._target and obj is not self._get_viewport(self._target):
            return False

        et = event.type()

        if et in (QEvent.DragEnter, QEvent.DragMove):
            md = getattr(event, 'mimeData', lambda: None)()
            if self._mime_supported(md):
                try:
                    event.setDropAction(Qt.CopyAction)
                    event.acceptProposedAction()
                except Exception:
                    event.accept()
                return True
            return False

        if et == QEvent.Drop:
            md = getattr(event, 'mimeData', lambda: None)()
            if not self._mime_supported(md):
                return False

            chat_input = self._process_drop(md)

            try:
                event.setDropAction(Qt.CopyAction)
                event.acceptProposedAction()
            except Exception:
                event.accept()

            # Policy decision:
            if self._policy == self.SWALLOW_ALL:
                # Consume the event; nothing else should handle it.
                return True

            if self._policy == self.INPUT_MIX:
                # For non-image payloads we allow default to insert text/paths into input.
                # To avoid duplicate attachments (insertFromMimeData calls handle_clipboard),
                # set a one-shot guard flag.
                if chat_input is not None and self._allow_default_text_insert_for_non_image(md):
                    try:
                        chat_input._skip_clipboard_on_next_insert = True
                    except Exception:
                        pass
                    return False  # let default drop insert text/paths
                else:
                    return True  # swallow images

            # Default: swallow
            return True

        return False
