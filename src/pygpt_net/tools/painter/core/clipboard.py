#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #


from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from pygpt_net.utils import trans


class Clipboard:
    """Painter clipboard operations on one canvas."""

    def __init__(self, canvas):
        self.canvas = canvas

    def paste(self) -> bool:
        """
        Paste text into the active Text-mode editor, otherwise paste an image
        from the clipboard into the Painter.

        :return: True if clipboard content was pasted
        """
        canvas = self.canvas
        if canvas.text.paste(canvas):
            return True

        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        if not source.hasImage():
            return False

        image = clipboard.image()
        if not isinstance(image, QImage) or image.isNull():
            return False

        canvas.text.cancel(canvas)
        canvas.document.set_image(image, fit_canvas_to_image=True)
        if canvas.window is not None:
            canvas.window.update_status(trans('clipboard.pasted'))
        return True

    def copy(self) -> bool:
        """
        Copy selected text from the active Text-mode editor, otherwise copy
        the current Painter image to the clipboard.

        :return: True if clipboard content was copied
        """
        canvas = self.canvas
        if canvas.text.copy():
            return True

        canvas.document.compose()
        if canvas.document.image is None or canvas.document.image.isNull():
            return False

        clipboard = QApplication.clipboard()
        clipboard.setImage(canvas.document.image)
        if canvas.window is not None:
            canvas.window.update_status(trans('clipboard.copied'))
        return True

