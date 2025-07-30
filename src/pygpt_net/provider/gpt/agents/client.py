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

import os

from openai import AsyncOpenAI
from agents import (
    Model,
    ModelProvider,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)

from pygpt_net.core.types import MODE_AGENT_OPENAI
from pygpt_net.item.model import ModelItem


class CustomModelProvider(ModelProvider):
    def __init__(self, client: AsyncOpenAI):
        """
        Custom Model Provider for OpenAI agents

        :param client: AsyncOpenAI client instance
        """
        super().__init__()
        self.client = client
        set_tracing_disabled(True)

    def get_model(self, model_name: str | None) -> Model:
        return OpenAIChatCompletionsModel(model=model_name, openai_client=self.client)


def get_custom_model_provider(window, model: ModelItem) -> CustomModelProvider:
    """
    Return custom OpenAI client for the specified model

    :param window: Window instance
    :param model: ModelItem instance
    :return: CustomModelProvider instance
    """
    args = window.core.models.prepare_client_args(MODE_AGENT_OPENAI, model)
    client = AsyncOpenAI(**args)
    return CustomModelProvider(client)

def get_client(window, model: ModelItem) -> AsyncOpenAI:
    """
    Return OpenAI client for the specified model

    :param window: Window instance
    :param model: ModelItem instance
    :return: AsyncOpenAI client instance
    """
    set_tracing_disabled(True)
    args = window.core.models.prepare_client_args(MODE_AGENT_OPENAI, model)
    return AsyncOpenAI(**args)

def set_openai_env(window):
    """
    Set OpenAI environment variables based on the window configuration

    :param window: Window instance
    """
    os.environ['OPENAI_API_KEY'] = str(window.core.config.get('api_key'))
    os.environ['OPENAI_API_BASE'] = str(window.core.config.get('api_endpoint'))
    os.environ['OPENAI_ORGANIZATION'] = str(window.core.config.get('organization_key'))