#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.13 16:00:00                  #
# ================================================== #

import os
import uuid

from pygpt_net.plugin.base.plugin import BasePlugin


class BaseProvider:
    AUDIO_OUTPUT_DIR = "audio_output"
    AUDIO_OUTPUT_MAX_FILES = 30

    def __init__(self, plugin=None):
        """
        Audio output base provider

        :param plugin: plugin instance
        """
        self.plugin = plugin
        self.id = ""  # unique provider id
        self.name = ""  # name to display

    def init(self, plugin: BasePlugin):
        """
        Initialize provider

        :param plugin: plugin instance
        """
        self.attach(plugin)
        self.init_options()

    def attach(self, plugin: BasePlugin):
        """
        Attach plugin instance

        :param plugin: plugin instance
        """
        self.plugin = plugin

    def init_options(self):
        """Initialize provider options (for plugin settings)"""
        pass

    def speech(self, text: str) -> str:
        """
        Speech text to audio

        :param text: text to speech
        :return: path to generated audio file or None if audio playback is handled here
        """
        pass

    def prepare_output_path(self, extension: str = None) -> str:
        """
        Prepare a unique path for generated audio and rotate old output files.

        :param extension: optional output extension override, e.g. ".wav"
        :return: path to a new audio output file
        """
        base_dir = self.plugin.window.core.config.path
        output_dir = os.path.join(base_dir, "tmp", self.AUDIO_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)

        # Keep room for the file that is about to be generated so the
        # directory never normally grows beyond AUDIO_OUTPUT_MAX_FILES.
        self._cleanup_output_dir(
            output_dir,
            max(0, self.AUDIO_OUTPUT_MAX_FILES - 1),
        )

        default_name = os.path.basename(
            getattr(self.plugin, "output_file", "output.mp3") or "output.mp3"
        )
        name_root, default_extension = os.path.splitext(default_name)
        if not name_root:
            name_root = "output"

        if extension is None:
            extension = default_extension
        elif extension and not extension.startswith("."):
            extension = f".{extension}"

        while True:
            filename = f"{name_root}_{uuid.uuid4().hex}{extension}"
            path = os.path.join(output_dir, filename)
            if not os.path.exists(path):
                return path

    @staticmethod
    def _cleanup_output_dir(output_dir: str, keep_files: int):
        """
        Delete the oldest files from the audio output directory.

        :param output_dir: audio output directory
        :param keep_files: number of existing files to retain
        """
        files = []
        try:
            names = os.listdir(output_dir)
        except OSError:
            return

        for name in names:
            path = os.path.join(output_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                modified = os.path.getmtime(path)
            except OSError:
                continue
            files.append((modified, path))

        files.sort(key=lambda item: item[0])
        to_remove = max(0, len(files) - keep_files)
        if to_remove == 0:
            return

        for _, path in files:
            if to_remove == 0:
                break
            try:
                os.remove(path)
                to_remove -= 1
            except FileNotFoundError:
                to_remove -= 1
            except OSError:
                # A file can still be held by the audio backend on Windows.
                # Try the next oldest file instead of failing TTS generation.
                continue

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        pass

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return "Google API key and CX ID are required for this command to work. " \
               "Please go to the plugin settings and enter your API key and CX ID."
