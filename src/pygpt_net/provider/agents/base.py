#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 03:00:00                  #
# ================================================== #

from typing import Dict, Any, Tuple

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.preset import PresetItem


class BaseAgent:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.type = ""
        self.mode = ""
        self.name = ""

    def get_mode(self) -> str:
        """
        Return Agent mode

        :return: Agent mode
        """
        return self.mode

    def get_agent(
            self,
            window,
            kwargs: Dict[str, Any]
    ) -> Any:
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        pass

    def get_options(self) -> dict:
        """
        Return Agent options

        :return: Agent options
        """
        return {}

    async def run(
            self,
            window,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            bridge = None,
    ) -> Tuple[str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for agent operations
        :return: Final output and response ID
        """
        pass

    def get_option(self, preset: PresetItem, section: str, key: str) -> Any:
        """
        Get specific option from preset

        :param preset: Preset item
        :param section: Section name
        :param key: Option key
        :return: Option value
        """
        extra = preset.extra
        if not isinstance(extra, dict) or self.id not in extra:
            return self.get_default(section, key)
        options = extra[self.id]
        if section not in options:
            return self.get_default(section, key)
        if key not in options[section]:
            return self.get_default(section, key)
        option = options[section][key]
        if option is None:
            return self.get_default(section, key)
        return option


    def get_default(self, section: str, key: str) -> Any:
        """
        Get default option value

        :param section: Section name
        :param key: Option key
        :return: Default option value
        """
        options = self.get_options()
        if section not in options:
            return
        if key not in options[section]['options']:
            return
        return options[section]['options'][key].get('default', None)

    def get_default_prompt(self) -> str:
        """
        Get default prompt for the agent

        :return: Default prompt string
        """
        options = self.get_options()
        if '__prompt__' in options:
            return options['__prompt__']
        return ""