#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.10 10:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from pygpt_net.utils import trans


class Drawing:
    def __init__(self, window=None):
        """
        Drawing controller

        :param window: Window instance
        """
        self.window = window

    def set_brush_mode(self, enabled):
        """
        Set the paint mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.setBrushColor(Qt.black)

    def set_erase_mode(self, enabled):
        """
        Set the erase mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.setBrushColor(Qt.white)

    def change_brush_size(self, size):
        """
        Change the brush size

        :param size: Brush size
        """
        self.window.ui.painter.setBrushSize(int(size))

    def change_brush_color(self):
        """
        Change the brush color

        :param color_name: Color name
        """
        color = self.window.ui.nodes['painter.select.brush.color'].currentData()
        self.window.ui.painter.setBrushColor(color)

    def capture(self):
        """Capture current image"""
        # clear attachments before capture if needed
        if self.window.controller.attachment.is_capture_clear():
            self.window.controller.attachment.clear(True)

        try:
            # prepare filename
            now = datetime.datetime.now()
            dt = now.strftime("%Y-%m-%d_%H-%M-%S")
            name = 'cap-' + dt
            path = os.path.join(self.window.core.config.path, 'capture', name + '.png')

            # capture
            self.window.ui.painter.image.save(path)
            mode = self.window.core.config.get('mode')

            # make attachment
            dt_info = now.strftime("%Y-%m-%d %H:%M:%S")
            title = trans('painter.capture.name.prefix') + ' ' + name
            title = title.replace('cap-', '').replace('_', ' ')
            self.window.core.attachments.new(mode, title, path, False)
            self.window.core.attachments.save()
            self.window.controller.attachment.update()

            # show last capture time in status
            self.window.statusChanged.emit(trans("painter.capture.manual.captured.success") + ' ' + dt_info)
            return True

        except Exception as e:
            print("Image capture exception", e)
            self.window.core.debug.log(e)

    def get_colors(self) -> dict:
        """
        Get colors dict

        :return: colors dict
        """
        return {
            "Black": Qt.black,
            "Red": Qt.red,
            "Orange": QColor('orange'),
            "Yellow": Qt.yellow,
            "Green": Qt.green,
            "Blue": Qt.blue,
            "Indigo": QColor('indigo'),
            "Violet": QColor('violet')
        }

    def get_sizes(self) -> list:
        """Get brush sizes"""
        return ['1', '2', '3', '5', '8', '12', '15', '20', '25', '30', '50', '100', '200']
