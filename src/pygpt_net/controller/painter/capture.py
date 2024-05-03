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

import datetime
import os

from PySide6.QtGui import QImage

from pygpt_net.utils import trans


class Capture:
    def __init__(self, window=None):
        """
        Painter capture controller

        :param window: Window instance
        """
        self.window = window

    def camera(self):
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

    def screenshot(self):
        """Make screenshot and append to attachments"""
        # switch to vision mode if needed
        self.window.controller.chat.vision.switch_to_vision()

        # clear attachments before capture if needed
        if self.window.controller.attachment.is_capture_clear():
            self.window.controller.attachment.clear(True, auto=True)

        try:
            # prepare filename
            now = datetime.datetime.now()
            dt = now.strftime("%Y-%m-%d_%H-%M-%S")
            name = 'cap-' + dt
            path = os.path.join(self.window.controller.painter.common.get_capture_dir(), name + '.png')

            # capture screenshot
            screen = self.window.app.primaryScreen()
            screenshot = screen.grabWindow(0)
            screenshot.save(path, 'png')
            self.attach(name, path, 'screenshot')
            self.window.controller.painter.open(path)

            # show last capture time in status
            dt_info = now.strftime("%Y-%m-%d %H:%M:%S")
            self.window.statusChanged.emit(trans("painter.capture.manual.captured.success") + ' ' + dt_info)
            return True

        except Exception as e:
            print("Screenshot capture exception", e)
            self.window.core.debug.log(e)

    def use(self):
        """Use current image"""
        # switch to vision mode if needed
        self.window.controller.chat.vision.switch_to_vision()

        # clear attachments before capture if needed
        if self.window.controller.attachment.is_capture_clear():
            self.window.controller.attachment.clear(True, auto=True)

        try:
            # prepare filename
            now = datetime.datetime.now()
            dt = now.strftime("%Y-%m-%d_%H-%M-%S")
            name = 'cap-' + dt
            path = os.path.join(self.window.controller.painter.common.get_capture_dir(), name + '.png')

            # capture
            self.window.ui.painter.image.save(path)
            self.attach(name, path)

            # show last capture time in status
            dt_info = now.strftime("%Y-%m-%d %H:%M:%S")
            self.window.statusChanged.emit(trans("painter.capture.manual.captured.success") + ' ' + dt_info)
            return True

        except Exception as e:
            print("Image capture exception", e)
            self.window.core.debug.log(e)

    def attach(self, name: str, path: str, type: str = 'drawing'):
        """
        Attach image to attachments

        :param name: image name
        :param path: image path
        :param type: capture type (drawing, screenshot)
        """
        mode = self.window.core.config.get('mode')
        if type == 'drawing':
            title = trans('painter.capture.name.prefix') + ' ' + name
        elif type == 'screenshot':
            title = trans('screenshot.capture.name.prefix') + ' ' + name
        else:
            title = name
        title = title.replace('cap-', '').replace('_', ' ')

        # make attachment
        self.window.core.attachments.new(mode, title, path, False)
        self.window.core.attachments.save()
        self.window.controller.attachment.update()
