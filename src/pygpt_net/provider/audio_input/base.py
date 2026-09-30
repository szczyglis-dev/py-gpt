#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from pygpt_net.core.locale import LocaleDomain
from pygpt_net.plugin.base.plugin import BasePlugin


class BaseProvider(LocaleDomain):
    def __init__(self, plugin=None):
        """
        Audio input base provider

        :param plugin: plugin instance
        """
        self.init_locale_domain()
        self.plugin = plugin
        self.id = ""  # unique provider id
        self.name = ""  # name to display

    def init(self, plugin: BasePlugin):
        """
        Initialize provider

        :param plugin: plugin instance
        """
        self.attach(plugin)
        domain = self.get_locale_domain()
        if domain and hasattr(plugin, "option_locale_domain"):
            if self.id:
                plugin.tab_locale_domains[self.id] = domain
            with plugin.option_locale_domain(domain):
                self.init_options()
        else:
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

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        pass

    def get_name(self) -> str:
        """Return localized provider name when the add-on domain defines it."""
        domain = self.get_locale_domain()
        if domain:
            value = self.trans("provider.name")
            if value != "provider.name":
                return value
        return self.name

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
        return ""
