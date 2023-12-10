#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.10 16:00:00                  #
# ================================================== #

import cv2

from PySide6.QtCore import QObject, Signal


class Camera:
    def __init__(self, config=None):
        """
        Camera

        :param config: config object
        """
        self.config = config
        self.capture = None
        self.current = None


class CameraThread(QObject):
    finished = Signal(object)
    destroyed = Signal()
    started = Signal()
    stopped = Signal()

    def __init__(self, window=None):
        """
        Camera capture thread
        """
        super().__init__()
        self.window = window
        self.initialized = False
        self.capture = None
        self.frame = None

    def setup_camera(self):
        """Initialize camera.
        """
        try:
            self.capture = cv2.VideoCapture(0)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.window.config.data['vision.capture.width'])
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.window.config.data['vision.capture.height'])
        except Exception as e:
            print("Camera thread exception:", e)
            self.finished.emit(e)

    def run(self):
        try:
            if not self.initialized:
                self.setup_camera()
                self.initialized = True

            print("Starting video capture thread....")
            while True:
                if self.window.is_closing or self.capture is None:
                    break
                _, frame = self.capture.read()
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.flip(frame, 1)
                self.window.controller.camera.frame = frame  # update frame
        except Exception as e:
            print("Camera thread exception:", e)
            self.finished.emit(e)
