#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.16 17:00:00                  #
# ================================================== #

import re
from typing import Union, Optional, Tuple, List

from PySide6.QtMultimedia import QMediaDevices
from bs4 import UnicodeDammit

from pygpt_net.provider.audio_input.base import BaseProvider as InputBaseProvider
from pygpt_net.provider.audio_output.base import BaseProvider as OutputBaseProvider

from .capture import Capture
from .whisper import Whisper


class Audio:
    def __init__(self, window=None):
        """
        Audio input/output core

        :param window: Window instance
        """
        self.window = window
        self.capture = Capture(window)
        self.whisper = Whisper(window)
        self.providers = {
            "input": {},
            "output": {},
        }
        self.last_error = None

    def get_input_devices(self) -> List[Tuple[int, str]]:
        """
        Get input devices

        :return devices list: [(id, name)]
        """
        devices = QMediaDevices.audioInputs()
        devices_list = []
        for index, device in enumerate(devices):
            dammit = UnicodeDammit(device.description())
            devices_list.append((index, dammit.unicode_markup))
        return devices_list

    def is_device_compatible(self, device_index: int) -> bool:
        """
        Check if device is compatible

        :param device_index: device index
        :return: True if compatible
        """
        import pyaudio
        rate = int(self.window.core.config.get('audio.input.rate', 44100))
        channels = int(self.window.core.config.get('audio.input.channels', 1))
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(device_index)
        try:
            p.is_format_supported(
                rate=rate,
                input_device=info['index'],
                input_channels=channels,
                input_format=pyaudio.paInt16)
            supported = True
        except ValueError as e:
            self.last_error = str(e)
            supported = False
        p.terminate()
        return supported

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
        return re.sub(r'~###~.*?~###~', '', str(text))

    def get_last_error(self) -> str:
        """
        Return last error

        :return: Error
        """
        return self.last_error
