#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.11 23:00:00                  #
# ================================================== #

import datetime
import math
import os
import mss
import mss.tools
from PIL import Image, ImageDraw
from pynput.mouse import Controller

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

    def capture_screen_with_custom_cursor(self, save_path: str, size: int = 8, rotation_angle: int = -30, opacity: float = 0.2) -> bool:
        """
        Capture screen with custom cursor

        :param save_path: Path to save
        :param size: Size
        :param rotation_angle: Rotation angle
        :param opacity: Halo opacity
        :return: True if success
        """
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

        mouse = Controller()
        cursor_x, cursor_y = mouse.position

        cursor_x -= monitor['left']
        cursor_y -= monitor['top']

        img = img.convert('RGBA')

        cursor_canvas_size = size * 6
        cursor_canvas = Image.new('RGBA', (cursor_canvas_size, cursor_canvas_size), (0, 0, 0, 0))
        draw_cursor = ImageDraw.Draw(cursor_canvas)

        cursor_color = (255, 255, 255, 255)
        outline_color = (0, 0, 0, 255)
        halo_color = (255, 255, 0, int(255 * opacity))
        outline_width = 2

        tip_x = cursor_canvas_size / 2
        tip_y = cursor_canvas_size / 2

        arrow_size = size
        arrow_shape = [
            (0, 0),
            (-arrow_size, arrow_size * 2),
            (-arrow_size * 0.5, arrow_size * 2),
            (-arrow_size * 0.5, arrow_size * 3),
            (arrow_size * 0.5, arrow_size * 3),
            (arrow_size * 0.5, arrow_size * 2),
            (arrow_size, arrow_size * 2),
        ]

        def rotate_point(x, y, angle):
            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            x_rot = x * cos_a - y * sin_a
            y_rot = x * sin_a + y * cos_a
            return x_rot, y_rot

        rotated_arrow_points = [
            (rotate_point(x, y, rotation_angle)[0] + tip_x, rotate_point(x, y, rotation_angle)[1] + tip_y)
            for x, y in arrow_shape
        ]

        outline_offset = outline_width
        outline_arrow_points = []
        for x, y in arrow_shape:
            dx = x
            dy = y
            dist = math.hypot(dx, dy)
            if dist != 0:
                scale = (dist + outline_offset) / dist
                x_out = dx * scale
                y_out = dy * scale
            else:
                x_out = dx
                y_out = dy
            x_rot, y_rot = rotate_point(x_out, y_out, rotation_angle)
            outline_arrow_points.append((x_rot + tip_x, y_rot + tip_y))

        halo_radius = size * 2
        halo_bbox = (
            int(tip_x - halo_radius),
            int(tip_y - halo_radius),
            int(tip_x + halo_radius),
            int(tip_y + halo_radius)
        )
        draw_cursor.ellipse(halo_bbox, fill=halo_color)
        draw_cursor.polygon(outline_arrow_points, fill=outline_color)
        draw_cursor.polygon(rotated_arrow_points, fill=cursor_color)

        paste_x = int(cursor_x - tip_x)
        paste_y = int(cursor_y - tip_y)
        img.paste(cursor_canvas, (paste_x, paste_y), cursor_canvas)

        img.save(save_path)
        return True

    def screenshot(self, attach_cursor: bool = False):
        """
        Make screenshot and append to attachments

        :param attach_cursor: True to with custom cursor
        """
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
