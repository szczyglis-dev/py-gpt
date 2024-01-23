#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor


class Common:
    def __init__(self, window=None):
        """
        Painter common methods controller

        :param window: Window instance
        """
        self.window = window

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

    def set_brush_mode(self, enabled: bool):
        """
        Set the paint mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.nodes['painter.select.brush.color'].setCurrentText("Black")
            self.window.ui.painter.set_brush_color(Qt.black)

    def set_erase_mode(self, enabled: bool):
        """
        Set the erase mode

        :param enabled: bool
        """
        if enabled:
            self.window.ui.nodes['painter.select.brush.color'].setCurrentText("White")
            self.window.ui.painter.set_brush_color(Qt.white)

    def change_canvas_size(self, selected=None):
        """
        Change the canvas size

        :param selected: Selected size
        """
        if not selected:
            selected = self.window.ui.nodes['painter.select.canvas.size'].currentData()
        if selected:
            size = self.convert_to_size(selected)
            self.window.ui.nodes['painter.select.canvas.size'].setCurrentText(selected)
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
        """Change the brush color"""
        color = self.window.ui.nodes['painter.select.brush.color'].currentData()
        self.window.ui.painter.set_brush_color(color)

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
        """
        Get brush sizes

        :return: list of sizes
        """
        return ['1', '2', '3', '5', '8', '12', '15', '20', '25', '30', '50', '100', '200']

    def get_canvas_sizes(self) -> list:
        """
        Get canvas sizes

        :return: list of sizes
        """
        return [
            "640x480", "800x600", "1024x768", "1280x720", "1600x900",
            "1920x1080", "2560x1440", "3840x2160", "4096x2160"
        ]

    def get_capture_dir(self) -> str:
        """
        Get capture directory

        :return: path to capture directory
        """
        return self.window.core.config.get_user_dir('capture')
