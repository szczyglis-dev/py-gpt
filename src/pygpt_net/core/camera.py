#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import os

import cv2

from PySide6.QtCore import QObject, Signal


class Camera:
    def __init__(self, window=None):
        """
        Camera handler

        :param window: Window instance
        """
        self.window = window
        self.capture = None
        self.current = None

    def install(self):
        """Install provider data"""
        img_dir = os.path.join(self.window.core.config.path, 'capture')
        if not os.path.exists(img_dir):
            os.mkdir(img_dir)


class CameraThread(QObject):
    finished = Signal()
    destroyed = Signal()
    started = Signal()
    stopped = Signal()

    def __init__(self, window=None):
        """
        Camera capture thread

        :param window: Window instance
        """
        super().__init__()
        self.window = window
        self.initialized = False
        self.capture = None
        self.frame = None

    def setup_camera(self):
        """Initialize camera"""
        try:
            # get params from global config
            self.capture = cv2.VideoCapture(self.window.core.config.get('vision.capture.idx'))
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.window.core.config.get('vision.capture.width'))
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.window.core.config.get('vision.capture.height'))
        except Exception as e:
            self.window.core.debug.log(e)
            print("Camera thread setup exception", e)
            self.finished.emit(e)

    def run(self):
        """Frame capture loop"""
        try:
            if not self.initialized:
                self.setup_camera()
                self.started.emit()
                self.initialized = True

            while True:
                if self.window.is_closing \
                        or self.capture is None \
                        or not self.capture.isOpened() \
                        or self.window.controller.camera.stop:
                    self.release()  # release camera
                    self.stopped.emit()
                    break
                _, frame = self.capture.read()
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.flip(frame, 1)
                self.window.controller.camera.frame = frame  # update frame
        except Exception as e:
            self.window.core.debug.log(e)
            print("Camera thread capture exception", e)

        # release camera
        self.release()
        self.finished.emit()

    def release(self):
        """Release camera"""
        if self.capture is not None and self.capture.isOpened():
            self.capture.release()
        self.capture = None
        self.frame = None
        self.initialized = False
