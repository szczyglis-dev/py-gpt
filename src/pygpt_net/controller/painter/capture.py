#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 19:15:00                  #
# ================================================== #

import datetime
import math
import os
from typing import Optional, Union

import mss
import mss.tools
from PIL import Image, ImageDraw
from pynput.mouse import Controller

from PySide6.QtCore import QRect
from PySide6.QtGui import QImage

from pygpt_net.core.events import KernelEvent
from pygpt_net.utils import trans


class Capture:
    # Hotspot of data/icons/cursor.png.  The PNG is 48x48 with transparent
    # padding; the actual arrow tip is at approximately (17, 11).  Keep the
    # hotspot explicit instead of centering the bitmap so screenshot
    # coordinates match the point that will actually be clicked.
    CURSOR_HOTSPOT = (17, 11)

    def __init__(self, window=None):
        """
        Painter capture controller

        :param window: Window instance
        """
        self.window = window

    def camera(self, show_flash: bool = True):
        """Get image from camera and put it on the Painter canvas."""
        if not self.window.controller.camera.is_enabled():
            self.window.controller.camera.enable_capture()
            self.window.controller.camera.setup_ui()
        frame = self.window.controller.camera.get_current_frame(False)
        if frame is None:
            return False
        height, width, channel = frame.shape
        bytes = 3 * width
        image = QImage(frame.data, width, height, bytes, QImage.Format_RGB888)
        self.window.ui.painter.set_image(image)
        if show_flash:
            self.window.ui.tray.show_capture_flash()
        return True

    def _overlay_custom_cursor(self, img: Image.Image, cursor_x: float, cursor_y: float) -> Image.Image:
        """Overlay the bundled cursor with its click hotspot at (cursor_x, cursor_y)."""
        x = int(round(cursor_x))
        y = int(round(cursor_y))

        # Do not render a clipped cursor from another monitor.  Computer Use
        # coordinates are relative to the monitor represented by this image.
        if x < 0 or y < 0 or x >= img.width or y >= img.height:
            return img.convert('RGBA')

        cursor_path = os.path.join(
            self.window.core.config.get_app_path(),
            "data",
            "icons",
            "cursor.png",
        )
        with Image.open(cursor_path) as source:
            cursor_img = source.convert('RGBA')

        hotspot_x, hotspot_y = self.CURSOR_HOTSPOT
        paste_x = x - hotspot_x
        paste_y = y - hotspot_y

        # alpha_composite uses the source alpha exactly once (unlike using the
        # same RGBA image as both source and paste mask) and clips cleanly at
        # image boundaries.
        result = img.convert('RGBA')
        result.alpha_composite(cursor_img, dest=(paste_x, paste_y))
        return result

    def capture_screen_with_custom_cursor(self, save_path: str) -> str:
        """
        Capture screen with custom cursor

        :param save_path: Save path
        :return: Save path
        """
        mouse = Controller()

        with mss.mss(with_cursor=False) as sct:
            monitor = sct.monitors[1]

            # Keep the cursor sample and screen grab coherent.  If the pointer
            # moves while the screenshot is being taken, retry once so hover
            # state, screenshot and cursor marker describe the same position as
            # closely as possible.
            screenshot = None
            cursor_pos = mouse.position
            for _ in range(2):
                before = mouse.position
                screenshot = sct.grab(monitor)
                after = mouse.position
                cursor_pos = after
                if tuple(before) == tuple(after):
                    cursor_pos = before
                    break

            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

        cursor_x = float(cursor_pos[0]) - float(monitor['left'])
        cursor_y = float(cursor_pos[1]) - float(monitor['top'])
        img = self._overlay_custom_cursor(img, cursor_x, cursor_y)
        img.save(save_path)
        return save_path

    def screenshot(
            self,
            attach_cursor: bool = False,
            silent: bool = False,
            append_to_ctx: bool = True
    ) -> Optional[Union[str, bool]]:
        """
        Make screenshot and append to attachments

        :param attach_cursor: True to with custom cursor
        :param silent: Silent mode
        :param append_to_ctx: If False, mark attachment as transport-only (do not persist/render in ctx)
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

            self.attach(name, path, 'screenshot', silent=silent, append_to_ctx=append_to_ctx)

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

    def screenshot_region(
            self,
            region: QRect,
            screen_geometry: QRect,
            screen_index: int = 0,
            silent: bool = False
    ) -> Optional[Union[str, bool]]:
        """
        Make a screenshot of a selected screen region and append it to attachments.

        :param region: selected region in global Qt coordinates
        :param screen_geometry: target QScreen geometry in global Qt coordinates
        :param screen_index: target QScreen index (0-based)
        :param silent: Silent mode
        :return: Path to screenshot or False if failed
        """
        if region is None or screen_geometry is None:
            return False
        if region.width() <= 1 or region.height() <= 1:
            return False
        if screen_geometry.width() <= 0 or screen_geometry.height() <= 0:
            return False

        if not silent:
            # switch to vision mode if needed
            self.window.controller.chat.vision.switch_to_vision()

            # clear attachments before capture if needed
            if self.window.controller.attachment.is_capture_clear():
                self.window.controller.attachment.clear(True, auto=True)

        try:
            now = datetime.datetime.now()
            dt = now.strftime("%Y-%m-%d_%H-%M-%S")
            name = 'cap-' + dt
            path = os.path.join(self.window.controller.painter.common.get_capture_dir(), name + '.png')

            with mss.mss(with_cursor=False) as sct:
                monitors = sct.monitors[1:]
                if not monitors:
                    return False

                monitor_idx = max(0, min(int(screen_index), len(monitors) - 1))
                monitor = monitors[monitor_idx]

                scale_x = monitor['width'] / float(screen_geometry.width())
                scale_y = monitor['height'] / float(screen_geometry.height())

                local_left = max(0, region.x() - screen_geometry.x())
                local_top = max(0, region.y() - screen_geometry.y())
                local_right = min(screen_geometry.width(), local_left + region.width())
                local_bottom = min(screen_geometry.height(), local_top + region.height())

                left = monitor['left'] + int(round(local_left * scale_x))
                top = monitor['top'] + int(round(local_top * scale_y))
                right = monitor['left'] + int(round(local_right * scale_x))
                bottom = monitor['top'] + int(round(local_bottom * scale_y))

                capture_region = {
                    'left': left,
                    'top': top,
                    'width': max(1, right - left),
                    'height': max(1, bottom - top),
                }
                sct_img = sct.grab(capture_region)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=path)

            self.attach(name, path, 'screenshot', silent=silent)

            if not silent:
                self.window.controller.painter.open(path)
                dt_info = now.strftime("%Y-%m-%d %H:%M:%S")
                event = KernelEvent(KernelEvent.STATUS, {
                    'status': trans("painter.capture.manual.captured.success") + ' ' + dt_info,
                })
                self.window.dispatch(event)
            return path

        except Exception as e:
            print("Screenshot region capture exception", e)
            self.window.core.debug.log(e)
            return False

    def screenshot_playwright(
            self,
            page,
            silent: bool = False,
            append_to_ctx: bool = True,
            attach_cursor: bool = False,
            cursor_position: Optional[tuple] = None
    ) -> Optional[Union[str, bool]]:
        """
        Make screenshot and append to attachments

        :param page : Playwright page
        :param silent: Silent mode
        :param append_to_ctx: If False, mark attachment as transport-only (do not persist/render in ctx)
        :param attach_cursor: If True, overlay the bundled cursor at cursor_position
        :param cursor_position: Pointer position in Playwright viewport (CSS) pixels
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

            # capture screenshot from page
            if page:
                page.screenshot(path=path, full_page=False)
            else:
                return False

            if attach_cursor and cursor_position is not None:
                with Image.open(path) as source:
                    img = source.convert('RGBA')

                cursor_x, cursor_y = cursor_position
                # Playwright mouse coordinates are CSS viewport pixels.  Scale
                # them to screenshot pixels when a non-1 device scale factor is
                # used so the cursor hotspot remains exact.
                viewport = getattr(page, "viewport_size", None)
                if isinstance(viewport, dict):
                    viewport_w = int(viewport.get("width", 0) or 0)
                    viewport_h = int(viewport.get("height", 0) or 0)
                    if viewport_w > 0 and viewport_h > 0:
                        cursor_x = float(cursor_x) * img.width / viewport_w
                        cursor_y = float(cursor_y) * img.height / viewport_h

                img = self._overlay_custom_cursor(img, cursor_x, cursor_y)
                img.save(path)

            self.attach(name, path, 'screenshot', silent=silent, append_to_ctx=append_to_ctx)

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
            silent: bool = False,
            append_to_ctx: bool = True
    ):
        """
        Attach image to attachments

        :param name: image name
        :param path: image path
        :param type: capture type (drawing, screenshot)
        :param silent: silent mode
        :param append_to_ctx: If False, attachment is available to the provider but hidden from ctx/UI
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
        extra = {"append_to_ctx": bool(append_to_ctx)}
        self.window.core.attachments.new(mode, title, path, False, extra=extra)
        self.window.core.attachments.save()

        if not silent:
            self.window.controller.attachment.update()
