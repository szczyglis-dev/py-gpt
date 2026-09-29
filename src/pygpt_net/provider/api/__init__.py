#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 14:40:00                  #
# ================================================== #

from threading import RLock

from pygpt_net.core.debug.loggers import ApiDebugLogger, ToolDebugLogger


class Api:
    """API wrapper registry with lazy provider initialization.

    Provider SDKs and their submodules are intentionally imported only when a
    provider is first accessed.  This keeps the public ``core.api.<provider>``
    interface unchanged while avoiding eager OpenAI/Google/Anthropic/xAI SDK
    imports during application startup.
    """

    def __init__(self, window=None):
        """
        API wrappers

        :param window: Window instance
        """
        self.window = window
        self.logger = ApiDebugLogger(window)
        self.tool_logger = ToolDebugLogger(window)
        self._anthropic = None
        self._google = None
        self._openai = None
        self._xai = None
        self._provider_lock = RLock()

    @property
    def anthropic(self):
        if self._anthropic is None:
            with self._provider_lock:
                if self._anthropic is None:
                    from .anthropic import ApiAnthropic
                    self._anthropic = ApiAnthropic(self.window)
        return self._anthropic

    @property
    def google(self):
        if self._google is None:
            with self._provider_lock:
                if self._google is None:
                    from .google import ApiGoogle
                    self._google = ApiGoogle(self.window)
        return self._google

    @property
    def openai(self):
        if self._openai is None:
            with self._provider_lock:
                if self._openai is None:
                    from .openai import ApiOpenAI
                    self._openai = ApiOpenAI(self.window)
        return self._openai

    @property
    def xai(self):
        if self._xai is None:
            with self._provider_lock:
                if self._xai is None:
                    from .x_ai import ApiXAI
                    self._xai = ApiXAI(self.window)
        return self._xai

    def stop(self):
        """Stop initialized API clients without creating unused providers."""
        for api in (self._anthropic, self._google, self._openai, self._xai):
            if api is not None:
                api.stop()

    def close(self):
        """Close initialized API clients without creating unused providers."""
        for api in (self._anthropic, self._google, self._openai, self._xai):
            if api is not None:
                api.safe_close()
