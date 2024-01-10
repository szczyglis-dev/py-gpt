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

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QImage

from pygpt_net.utils import trans


class Drawing:
    def __init__(self, window=None):
        """
        Drawing controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup drawing"""
        self.restore_current()
        size = "800x600"  # default size
        if self.window.core.config.has('painter.canvas.size'):
            size = self.window.core.config.get('painter.canvas.size')
        self.window.ui.nodes['painter.select.canvas.size'].setCurrentText(size)
        self.change_canvas_size(size)

    def is_drawing(self):
        """Check if drawing is enabled"""
        return self.window.controller.ui.output_tab_idx == 3

    def convert_to_size(self, canvas_size: str) -> tuple:
        """
        Convert string to size

        :param canvas_size: Canvas size string
        :return: tuple (width, height)
        """
        return tuple(map(int, canvas_size.split('x'))) if canvas_size else (0, 0)

    def set_canvas_size(self, width: int, height: int):
        """
        Set canvas size

        :param width: int
        :param height: int
        """
        self.window.ui.painter.setFixedSize(QSize(width, height))

    def from_camera(self):
        """Get image from camera"""
        if not self.window.controller.camera.is_enabled():
            self.window.controller.camera.enable_capture()
            self.window.controller.camera.setup_ui()
        frame = self.window.controller.camera.get_current_frame(False)
        if frame is None:
            return
        height, width, channel = frame.shape
        bytes = 3 * width
        image = QImage(frame.data, width, height, bytes, QImage.Format_RGB888)
        self.window.ui.painter.set_image(image)

    def restore_current(self):
        """Restore previous image"""
        path = os.path.join(self.window.core.config.path, 'capture', '_current.png')
        if os.path.exists(path):
            self.window.ui.painter.image.load(path)
            self.window.ui.painter.update()

    def save_all(self):
        """Save all (on exit)"""
        self.save_current()

    def save_current(self):
        """
        Store current image
        """
        path = os.path.join(self.window.core.config.path, 'capture', '_current.png')
        self.window.ui.painter.image.save(path)

    def set_brush_mode(self, enabled: bool):
        """
        Set the paint mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.set_brush_color(Qt.black)

    def set_erase_mode(self, enabled: bool):
        """
        Set the erase mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.painter.set_brush_color(Qt.white)

    def change_canvas_size(self, selected=None):
        """Change the canvas size"""
        if not selected:
            selected = self.window.ui.nodes['painter.select.canvas.size'].currentData()
        if selected:
            size = self.convert_to_size(selected)
            self.set_canvas_size(size[0], size[1])
            self.window.core.config.set('painter.canvas.size', selected)
            self.window.core.config.save()

    def change_brush_size(self, size):
        """
        Change the brush size

        :param size: Brush size
        """
        self.window.ui.painter.set_brush_size(int(size))

    def change_brush_color(self):
        """
        Change the brush color

        :param color_name: Color name
        """
        color = self.window.ui.nodes['painter.select.brush.color'].currentData()
        self.window.ui.painter.set_brush_color(color)

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
            "White": Qt.white,
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

    def get_canvas_sizes(self):
        """Get canvas sizes"""
        return [
            "640x480", "800x600", "1024x768", "1280x720", "1600x900",
            "1920x1080", "2560x1440", "3840x2160", "4096x2160"
        ]
