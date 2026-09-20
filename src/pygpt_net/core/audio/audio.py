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

import hashlib
import os
import re
from typing import Union, Optional, Tuple, List

from bs4 import BeautifulSoup

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

    def setup(self):
        """Initialize audio core"""
        self.capture.setup()
        self.output.setup()

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

    def get_memory_excluded_bytes(self) -> int:
        """
        Return memory that should not count towards renderer auto-cleanup.

        Audio providers may run native runtimes in the main process (for
        example local Whisper/Torch). Such memory is unrelated to WebEngine
        rendering, so providers can report an estimated resident footprint to
        exclude from the renderer threshold.
        """
        total = 0
        for providers in self.providers.values():
            for provider in providers.values():
                getter = getattr(provider, "get_memory_excluded_bytes", None)
                if not callable(getter):
                    continue
                try:
                    total += max(0, int(getter()))
                except Exception:
                    pass
        return total

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
        if text is None:
            return ""

        value = str(text)

        # Internal blocks are not user-facing prose and must never be spoken.
        for tag in ("tool", "think", "execute"):
            value = re.sub(
                rf'<{tag}\b[^>]*>.*?</{tag}>',
                '',
                value,
                flags=re.IGNORECASE | re.DOTALL,
            )

        # Keep only the visible label of Markdown links and drop image markup.
        value = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', value)
        value = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', value)

        # Preserve code contents but remove Markdown delimiters and formatting.
        value = re.sub(r'^\s{0,3}```[^\n]*$', '', value, flags=re.MULTILINE)
        value = re.sub(r'^\s{0,3}~~~[^\n]*$', '', value, flags=re.MULTILINE)
        value = re.sub(r'`([^`]+)`', r'\1', value)
        value = re.sub(r'~~(.*?)~~', r'\1', value, flags=re.DOTALL)
        value = re.sub(r'\*\*(.*?)\*\*', r'\1', value, flags=re.DOTALL)
        value = re.sub(r'__(.*?)__', r'\1', value, flags=re.DOTALL)
        value = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', value)
        value = re.sub(r'(?<!_)_([^_]+)_(?!_)', r'\1', value)

        # Strip block-level Markdown syntax while retaining its textual content.
        value = re.sub(r'^\s{0,3}#{1,6}\s*', '', value, flags=re.MULTILINE)
        value = re.sub(r'^\s*>+\s?', '', value, flags=re.MULTILINE)
        value = re.sub(r'^\s*[-+*]\s+', '', value, flags=re.MULTILINE)
        value = re.sub(r'^\s*\d+[.)]\s+', '', value, flags=re.MULTILINE)
        value = re.sub(r'^\s*(?:[-*_]\s*){3,}$', '', value, flags=re.MULTILINE)
        value = re.sub(
            r'^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$',
            '',
            value,
            flags=re.MULTILINE,
        )
        value = value.replace('|', ' ')

        # Remove HTML/XML tags while preserving their visible text.
        try:
            soup = BeautifulSoup(value, 'html.parser')
            for node in soup.find_all(['img', 'script', 'style']):
                node.decompose()
            value = soup.get_text(separator='\n')
            soup.decompose()
        except Exception:
            value = re.sub(r'<[^>]+>', '', value)

        # Unescape common Markdown escapes after markup has been removed.
        value = re.sub(r'\\([\\`*_{}\[\]()#+\-.!>])', r'\1', value)

        lines = []
        for line in value.splitlines():
            line = re.sub(r'\s+', ' ', line).strip()
            if line:
                lines.append(line)
        return '\n'.join(lines)

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
