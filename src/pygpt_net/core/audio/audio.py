#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.07 22:00:00                  #
# ================================================== #

import hashlib
import os
import re
from typing import Union, Optional, Tuple, List

from pygpt_net.provider.audio_input.base import BaseProvider as InputBaseProvider
from pygpt_net.provider.audio_output.base import BaseProvider as OutputBaseProvider

from .capture import Capture
from .output import Output
from .whisper import Whisper


class Audio:

    CACHE_FORMAT = "mp3"  # default cache format

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

    def prepare_cache_path(self, content: str) -> Tuple[Union[str, None], bool]:
        """
        Prepare unique cache file name for given content

        :param content: text content to generate cache file name
        :return: cache file path or None if content is empty
        """
        exists = False
        if not content:
            return None, exists
        sha1sum = hashlib.sha1(content.encode('utf-8')).hexdigest()
        filename = f"{sha1sum}." + self.CACHE_FORMAT
        tmp_dir = self.get_cache_dir()
        path = os.path.join(tmp_dir, filename)
        if os.path.exists(path):
            exists = True
        return str(path), exists

    def get_cache_dir(self) -> str:
        """
        Get cache directory for audio files

        :return: audio cache directory path
        """
        dir = self.window.core.config.get_user_dir("tmp")
        if not os.path.exists(dir):
            os.makedirs(dir, exist_ok=True)
        tmp_dir = os.path.join(dir, "audio_cache")
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir

    def delete_old_cache(self, max_files: int = 10):
        """
        Delete old cache files, keeping only the most recent ones.

        :param max_files: Maximum number of cache files to keep.
        """
        max_files = max_files - 1  # Reserve one file for the current cache
        max_files = max(1, max_files)  # Ensure at least one file is kept
        tmp_dir = self.get_cache_dir()
        files = [os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.endswith('.' + self.CACHE_FORMAT)]
        files.sort(key=os.path.getmtime, reverse=True)
        for file in files[max_files:]:
            try:
                os.remove(file)
            except Exception as e:
                print(f"Error deleting cache file {file}: {e}")

    def mp3_to_wav(
            self,
            src_file: str,
            dst_file: Optional[str] = None
    ) -> Union[str, None]:
        """
        Convert MP3 file to WAV format

        :param src_file: Path to the source MP3 file
        :param dst_file: Optional path for the destination WAV file.
        :return: Path to the converted WAV file or None if conversion fails.
        """
        from pydub import AudioSegment
        try:
            mp3_audio = AudioSegment.from_mp3(src_file)
        except Exception as e:
            print(f"Error loading mp3 file: {e}")
            print("Please install ffmpeg to handle mp3 files: https://ffmpeg.org/")
            return
        if dst_file is None:
            dir = os.path.dirname(src_file)
            filename = os.path.splitext(os.path.basename(src_file))[0] + ".wav"
            dst_file = os.path.join(dir, filename)
        try:
            mp3_audio.export(dst_file, format="wav")
            return str(dst_file)
        except Exception as e:
            print(f"Error exporting wav file: {e}")
            return
