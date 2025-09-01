#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

from typing import List, Tuple

from .backend.native import NativeBackend
from .backend.pyaudio import PyaudioBackend
from .backend.pygame import PygameBackend

class Output:

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
        backend = self.window.core.config.get("audio.output.backend", "native")
        if backend not in self.backends:
            print("Invalid audio backend specified, falling back to 'native'")
            backend = "native"
        return self.backends[backend]

    def setup(self):
        """Setup audio input backend"""
        for b in self.backends.values():
            b.set_rt_signals(self.window.controller.realtime.signals)

    def play(
            self,
            audio_file: str,
            event_name: str,
            stopped: callable,
            signals=None
    ):
        """
        Start audio playback

        :param audio_file: Path to audio file
        :param event_name: Event name to emit on playback
        :param stopped: Callback to call when playback is stopped
        :param signals: Signals to emit on playback
        :return: True if started
        """
        return self.get_backend().play(
            audio_file=audio_file,
            event_name=event_name,
            stopped=stopped,
            signals=signals
        )

    def stop(self, signals=None) -> bool:
        """
        Stop audio input recording

        :param signals: Signals to emit on stop
        :return: True if stopped
        """
        return self.get_backend().stop_playback(signals=signals)

    def get_output_devices(self) -> List[Tuple[int, str]]:
        """
        Get output devices

        :return devices list: [(id, name)]
        """
        return self.get_backend().get_output_devices()

    def get_default_output_device(self) -> Tuple[int, str]:
        """
        Get default output device

        :return: (id, name)
        """
        return self.get_backend().get_default_output_device()

    def handle_realtime(self, payload, signals):
        """
        Handle real-time audio playback
        """
        #self.get_backend().set_signals(signals)
        self.get_backend().handle_realtime(payload)