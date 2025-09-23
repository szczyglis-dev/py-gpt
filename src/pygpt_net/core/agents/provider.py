#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 00:00:00                  #
# ================================================== #

import copy
from typing import List, Dict, Any, Optional

from pygpt_net.core.types import MODE_CHAT, MODE_AGENT_LLAMA
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.agents.base import BaseAgent


class Provider:
    def __init__(self, window=None):
        """
        Agent providers

        :param window: Window instance
        """
        self.window = window
        self.agents = {}
        self.hidden = ["openai_custom", "llama_custom"]  # builder hidden agents (hide provider on list)

    def get_ids(self) -> List[str]:
        """
        Get agent providers ids

        :return: agent providers ids
        """
        return list(self.agents.keys())

    def has(self, id: str, mode: str = MODE_AGENT_LLAMA) -> bool:
        """
        Check if agent exists

        :param id: agent id
        :param mode: agent mode, used for custom agents (optional)
        :return: True if exists
        """
        custom = self.get_custom(id, mode) # shared instance
        if custom is not None:
            return True
        return id in self.agents

    def get(self, id: str, mode: str = MODE_AGENT_LLAMA) -> BaseAgent:
        """
        Get agent provider

        :param id: agent id
        :param mode: agent mode, used for custom agents (optional)
        :return: agent provider
        """
        # custom agents
        custom = self.get_custom(id, mode)  # shared instance
        if custom is not None:
            return custom

        # predefined agents
        if id in self.agents:
            return self.agents[id]

    def get_custom(
            self,
            id: str,
            mode: str = MODE_AGENT_LLAMA,
            as_copy: bool = True
    ) -> Optional[BaseAgent]:
        """
        Get custom agent provider by id

        :param id: agent id
        :param mode: agent mode, used for custom agents (optional)
        :param as_copy: return a copy of the agent (default: False)
        :return: custom agent provider
        """
        custom = None
        if self.window and self.window.core.agents.custom.is_custom(id):
            try:
                if mode == MODE_AGENT_LLAMA:
                    if "llama_custom" in self.agents:
                        custom = copy.deepcopy(self.agents["llama_custom"]) if as_copy else self.agents["llama_custom"]
                else:
                    if "openai_custom" in self.agents:
                        custom = copy.deepcopy(self.agents["openai_custom"]) if as_copy else self.agents["openai_custom"]
            except Exception as e:
                self.window.core.debug.log(f"Failed to get custom agent '{id}': {e}")
                return None

        # append custom id and build options
        if custom is not None:
            options = self.window.core.agents.custom.build_options(id)
            custom.set_id(id)
            custom.set_options(options)
        return custom

    def all(self) -> Dict[str, BaseAgent]:
        """
        Get all agents (predefined + custom, for build options)

        :return: dict of agent providers
        """
        all_agents = {}

        # predefined agents
        for id in self.get_ids():
            if id in self.hidden:
                continue
            all_agents[id] = self.agents[id]

        # custom agents
        if self.window:
            for id in self.window.core.agents.custom.get_ids():
                all_agents[id] = self.get_custom(id, as_copy=True)  # copy to avoid overwriting options
        return all_agents


    def register(self, id: str, agent):
        """
        Register Agent provider

        :param id: Agent id
        :param agent: Agent provider
        """
        self.agents[id] = agent

    def get_providers(self) -> List[str]:
        """
        Get agent providers list

        :return: list of agent providers
        """
        return self.get_ids()

    def get_choices(self, type: str = None) -> List[dict]:
        """
        Get agent providers choices

        :param type: filter by agent type (optional)
        :return: list of agent providers choices
        """
        choices = []
        for id in self.get_ids():
            if id in self.hidden:
                continue
            agent = self.get(id)
            if type is not None:
                if agent.type != type:
                    continue
            choices.append({id: agent.name})

        # sort by name
        if self.window:
            custom = self.window.core.agents.custom.get_choices()
            choices.extend(custom)
        choices.sort(key=lambda x: list(x.values())[0].lower())
        return choices

    def get_openai_model(self, model: ModelItem) -> Any:
        """
        Get OpenAI model by model id

        :param model: ModelItem
        :return: OpenAI model provider
        """
        from openai import AsyncOpenAI
        from agents import (
            OpenAIChatCompletionsModel,
        )
        models = self.window.core.models
        if isinstance(model, str):
            model = models.get(model)

        model_id = model.id
        if model.provider in ("openai", "azure_openai"):
            return model.id
        elif model.provider == "open_router":
            model_id = models.get_openrouter_model(model)

        args = models.prepare_client_args(MODE_CHAT, model)
        return OpenAIChatCompletionsModel(
            model=model_id,
            openai_client=AsyncOpenAI(**args),
        )