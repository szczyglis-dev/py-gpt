#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

from typing import Dict, Any, Tuple

from pygpt_net.item.ctx import CtxItem


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

    async def run(
            self,
            window,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            stopped: callable = None,
            on_step: callable = None,
            on_stop: callable = None,
            on_error: callable = None,
    ) -> Tuple[str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param stopped: Callback for stop event received from the user
        :param on_step: Callback for each step
        :param on_stop: Callback for stopping the process
        :param on_error: Callback for error handling
        :return: Final output and response ID
        """
        pass