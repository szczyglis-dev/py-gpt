#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import datetime
import math
import os
from typing import Optional, Union

import mss
import mss.tools
from PIL import Image, ImageDraw
from pynput.mouse import Controller

from PySide6.QtGui import QImage

from pygpt_net.core.events import KernelEvent
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

    def capture_screen_with_custom_cursor(self, save_path: str) -> str:
        """
        Capture screen with custom cursor

        :param save_path: Save path
        :return: Save path
        """
        cursor_path = os.path.join(self.window.core.config.get_app_path(), "data", "icons", "cursor.png")

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

        mouse = Controller()
        cursor_x, cursor_y = mouse.position

        cursor_x -= monitor['left']
        cursor_y -= monitor['top']

        img = img.convert('RGBA')

        cursor_img = Image.open(cursor_path).convert('RGBA')
        cursor_width, cursor_height = cursor_img.size

        paste_x = int(cursor_x - 20)
        paste_y = int(cursor_y - 20)

        img.paste(cursor_img, (paste_x, paste_y), cursor_img)

        img.save(save_path)
        return save_path

    def screenshot(
            self,
            attach_cursor: bool = False,
            silent: bool = False
    ) -> Optional[Union[str, bool]]:
        """
        Make screenshot and append to attachments

        :param attach_cursor: True to with custom cursor
        :param silent: Silent mode
        :return: Path to screenshot or False if failed
        """
        if not silent:
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
            if attach_cursor:
                if not self.capture_screen_with_custom_cursor(path):  # capture with custom cursor
                    return False
            else:
                with mss.mss(with_cursor=False) as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=path)

            self.attach(name, path, 'screenshot', silent=silent)

            if not silent:
                self.window.controller.painter.open(path)
                # show last capture time in status
                dt_info = now.strftime("%Y-%m-%d %H:%M:%S")
                event = KernelEvent(KernelEvent.STATUS, {
                    'status': trans("painter.capture.manual.captured.success") + ' ' + dt_info,
                })
                self.window.dispatch(event)
            return path

        except Exception as e:
            print("Screenshot capture exception", e)
            self.window.core.debug.log(e)

    def use(self):
        """Use current image"""
        # switch to vision mode if needed
        # self.window.controller.chat.vision.switch_to_vision()

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
            event = KernelEvent(KernelEvent.STATUS, {
                'status': trans("painter.capture.manual.captured.success") + ' ' + dt_info,
            })
            self.window.dispatch(event)
            return True

        except Exception as e:
            print("Image capture exception", e)
            self.window.core.debug.log(e)

    def attach(
            self,
            name: str,
            path: str,
            type: str = 'drawing',
            silent: bool = False
    ):
        """
        Attach image to attachments

        :param name: image name
        :param path: image path
        :param type: capture type (drawing, screenshot)
        :param silent: silent mode
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

        if not silent:
            self.window.controller.attachment.update()
