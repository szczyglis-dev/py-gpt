#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.28 08:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, QEvent, Qt


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