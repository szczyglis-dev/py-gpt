#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.07 03:00:00                  #
# ================================================== #

import re
from typing import Union, Optional, Tuple, List

from pygpt_net.provider.audio_input.base import BaseProvider as InputBaseProvider
from pygpt_net.provider.audio_output.base import BaseProvider as OutputBaseProvider

from .capture import Capture
from .output import Output
from .whisper import Whisper


class Audio:
    def __init__(self, window=None):
        """
        Audio input/output core

        :param window: Window instance
        """
        self.window = window
        self.capture = Capture(window)
        self.output = Output(window)
        self.whisper = Whisper(window)
        self.providers = {
            "input": {},  # audio transcription providers
            "output": {}, # speech synthesis providers
        }
        self.last_error = None

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
        return self.capture.get_input_devices()

    def get_output_devices(self) -> List[Tuple[int, str]]:
        """
        Get output devices

        :return devices list: [(id, name)]
        """
        return self.output.get_output_devices()

    def get_input_backends(self) -> List[Tuple[str, str]]:
        """
        Get input backends

        :return backends list: [(id, name)]
        """
        choices = []
        choices.append(("native", "Native / QtMultimedia"))
        choices.append(("pyaudio", "PyAudio"))
        choices.append(("pygame", "PyGame"))
        return choices

    def get_output_backends(self) -> List[Tuple[str, str]]:
        """
        Get output backends

        :return backends list: [(id, name)]
        """
        choices = []
        choices.append(("native", "Native / QtMultimedia"))
        choices.append(("pyaudio", "PyAudio"))
        # choices.append(("pygame", "PyGame"))
        return choices

    def get_default_input_device(self) -> Tuple[int, str]:
        """
        Get default input device

        :return: (id, name)
        """
        return self.capture.get_default_input_device()

    def get_default_output_device(self) -> Tuple[int, str]:
        """
        Get default output device

        :return: (id, name)
        """
        return self.output.get_default_output_device()

    def is_registered(self, id: str, type: str = "output") -> bool:
        """
        Check if provider is registered

        :param id: provider id
        :param type: provider type
        :return: True if registered
        """
        if type in self.providers:
            return id in self.providers[type]
        return False

    def get_providers(self, type: str = "output") -> dict:
        """
        Get all providers

        :param type: provider type
        :return: providers dict
        """
        if type in self.providers:
            return self.providers[type]
        return {}

    def get_ids(self, type: str = "output") -> list:
        """
        Get all providers ids

        :param type: provider type
        :return: providers ids list
        """
        if type in self.providers:
            return list(self.providers[type].keys())
        return []

    def get(
            self,
            id: str,
            type: str = "output"
    ) -> Optional[Union[InputBaseProvider, OutputBaseProvider]]:
        """
        Get provider instance

        :param id: provider id
        :param type: provider type
        :return: provider instance
        """
        if self.is_registered(id, type):
            return self.providers[type][id]
        return None

    def register(
            self,
            provider: Union[InputBaseProvider, OutputBaseProvider],
            type: str = "output"
    ):
        """
        Register provider

        :param provider: provider instance
        :param type: provider type
        """
        id = provider.id
        self.providers[type][id] = provider

    def clean_text(self, text: str) -> str:
        """
        Clean text before send to audio synthesis

        :param text: text
        :return: cleaned text
        """
        return re.sub(r'<tool>.*?</tool>', '', str(text))

    def get_last_error(self) -> str:
        """
        Return last error

        :return: Error
        """
        return self.last_error
