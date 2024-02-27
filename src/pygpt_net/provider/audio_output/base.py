#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 04:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin


class BaseProvider:
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
