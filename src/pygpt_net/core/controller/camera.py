#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.10 17:00:00                  #
# ================================================== #
import datetime
import os
import threading
import cv2

from PySide6.QtGui import QImage, QPixmap, Qt
from ..camera import CameraThread
from ..utils import trans


class Camera:
    def __init__(self, window=None):
        """
        Camera controller

        :param window: main window
        """
        self.window = window
        self.thread = None
        self.frame = None
        self.thread_started = False
        self.is_capture = False
        self.auto = False

    def setup(self):
        """
        Setup camera
        """
        if self.is_capture and not self.thread_started:
            self.start()

    def start(self):
        """
        Start camera thread
        """
        if self.thread_started:
            return
        thread = CameraThread(window=self.window)
        self.thread = threading.Thread(target=thread.run)
        self.thread.start()
        self.thread_started = True

    def update(self):
        """
        Update camera frame
        """
        if self.thread is None or not self.thread_started or self.frame is None or not self.is_capture:
            return
        label_width = self.window.data['video.preview'].video.width()
        image = QImage(self.frame, self.frame.shape[1], self.frame.shape[0],
                       self.frame.strides[0], QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(label_width, pixmap.height(),
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.window.data['video.preview'].video.setPixmap(scaled_pixmap)

    def capture_frame(self, switch=True):
        """
        Capture frame and save to attachments
        """
        # prepare name from date timestamp (using date)
        name = 'cap-' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        path = os.path.join(self.window.config.path, 'capture', name + '.jpg')
        compression_params = [cv2.IMWRITE_JPEG_QUALITY, 80]
        frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
        cv2.imwrite(path, frame, compression_params)
        mode = self.window.config.data['mode']
        self.window.controller.attachment.attachments.new(mode, 'Camera capture: ' + name, path, False)
        self.window.controller.attachment.attachments.save()
        self.window.controller.attachment.update()

        # switch to attachments tab
        if switch:
            self.window.tabs['input'].setCurrentIndex(1)  # switch to attachments tab

    def show_camera(self):
        """
        Show camera
        """
        self.window.data['video.preview'].setVisible(True)

    def hide_camera(self):
        """
        Hide camera
        """
        self.window.data['video.preview'].setVisible(False)

    def enable_capture(self):
        """
        Enable capture
        """
        if self.window.config.data['mode'] != 'vision':
            return
        self.is_capture = True
        self.window.config.data['vision.capture.enabled'] = True
        if not self.thread_started:
            self.start()

    def disable_capture(self):
        """
        Disable capture
        """
        if self.window.config.data['mode'] != 'vision':
            return
        self.is_capture = False
        self.window.config.data['vision.capture.enabled'] = False

    def toggle(self, state):
        """
        Toggle camera

        :param state: state
        """
        if state:
            self.enable_capture()
        else:
            self.disable_capture()

    def enable_auto(self):
        """
        Enable capture
        """
        if self.window.config.data['mode'] != 'vision':
            return
        self.auto = True
        self.window.config.data['vision.capture.auto'] = True
        self.window.data['video.preview'].label.setText(trans("vision.capture.auto.label"))

    def disable_auto(self):
        """
        Disable capture
        """
        if self.window.config.data['mode'] != 'vision':
            return
        self.auto = False
        self.window.config.data['vision.capture.auto'] = False
        self.window.data['video.preview'].label.setText(trans("vision.capture.label"))

    def toggle_auto(self, state):
        """
        Toggle camera

        :param state: state
        """
        if state:
            self.enable_auto()
        else:
            self.disable_auto()

    def is_enabled(self):
        """
        Check if camera is enabled

        :return: True if enabled, False otherwise
        """
        return self.is_capture

    def is_auto(self):
        """
        Check if camera is enabled

        :return: True if enabled, False otherwise
        """
        return self.auto

    def setup_settings(self):
        """
        Update layout checkboxes
        """
        if self.window.config.data['vision.capture.enabled']:
            self.is_capture = True
            self.window.data['vision.capture.enable'].setChecked(True)
        else:
            self.is_capture = False
            self.window.data['vision.capture.enable'].setChecked(False)

        if self.window.config.data['vision.capture.auto']:
            self.auto = True
            self.window.data['vision.capture.auto'].setChecked(True)
        else:
            self.auto = False
            self.window.data['vision.capture.auto'].setChecked(False)
