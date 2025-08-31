#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.27 07:00:00                  #
# ================================================== #

from typing import List, Tuple

from .backend.native import NativeBackend
from .backend.pyaudio import PyaudioBackend
from .backend.pygame import PygameBackend

class Capture:

    def __init__(self, window=None):
        """
        Audio input capture core

        :param window: Window instance
        """
        self.window = window
        self.backends = {
            "native": NativeBackend(self.window),
            "pyaudio": PyaudioBackend(self.window),
            "pygame": PygameBackend(self.window)
        }

    def get_backend(self):
        """
        Get audio backend instance based on configuration

        :return: backend instance
        """
        backend = self.window.core.config.get("audio.input.backend", "native")
        if backend not in self.backends:
            print("Invalid audio backend specified, falling back to 'native'")
            backend = "native"
        return self.backends[backend]

    def setup(self):
        """Setup audio input backend"""
        for b in self.backends.values():
            b.set_rt_signals(self.window.controller.realtime.signals)

    def get_default_input_device(self) -> Tuple[int, str]:
        """
        Get default input device

        :return: (id, name)
        """
        return self.get_backend().get_default_input_device()

    def set_repeat_callback(self, callback):
        """
        Set callback to be called on loop recording

        :param callback: function to call on loop recording
        """
        self.get_backend().set_repeat_callback(callback)

    def set_mode(self, mode: str):
        """
        Set input mode (input|control)

        :param mode: mode name
        """
        self.get_backend().set_mode(mode)

    def set_loop(self, loop: bool):
        """
        Set loop recording

        :param loop: True to enable loop recording
        """
        self.get_backend().set_loop(loop)

    def set_path(self, path: str):
        """
        Set audio input file path

        :param path: file path
        """
        self.get_backend().set_path(path)

    def start(self):
        """
        Start audio input recording

        :return: True if started
        """
        return self.get_backend().start()

    def stop(self):
        """
        Stop audio input recording

        :return: True if stopped
        """
        return self.get_backend().stop()

    def has_source(self) -> bool:
        """
        Check if audio source is available

        :return: True if available
        """
        return self.get_backend().has_source()

    def has_frames(self) -> bool:
        """
        Check if audio frames are available

        :return: True if available
        """
        return self.get_backend().has_frames()

    def has_min_frames(self) -> bool:
        """
        Check if min required audio frames

        :return: True if min frames
        """
        return self.get_backend().has_min_frames()

    def reset_audio_level(self):
        """Reset the audio level bar"""
        self.get_backend().reset_audio_level()

    def check_audio_input(self) -> bool:
        """
        Check if default audio input device is working

        :return: True if working
        """
        return self.get_backend().check_audio_input()

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
        return self.get_backend().get_input_devices()