#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 03:00:00                  #
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
        self.custom_id = None
        self.custom_options = None
        self.custom_schema = None

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

    def set_id(self, id: str):
        """
        Set custom ID for the agent

        :param id: Custom ID
        """
        self.custom_id = id

    def set_schema(self, schema: list):
        """
        Set custom schema for the agent

        :param schema: Custom schema
        """
        self.custom_schema = schema


    def set_options(self, options: dict):
        """
        Set custom options for the agent

        :param options: Custom options
        """
        self.custom_options = options

    def get_options(self) -> dict:
        """
        Return Agent options

        :return: Agent options
        """
        if self.custom_options is not None:
            return self.custom_options
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
    ) -> Tuple[CtxItem, str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for agent operations
        :return: Current ctx, final output, last response ID
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
        if preset is None:
            print("No preset provided, returning default option value")
            return None
        extra = preset.extra
        agent_id = self.custom_id if self.custom_id is not None else self.id
        if not isinstance(extra, dict) or agent_id not in extra:
            return self.get_default(section, key)
        options = extra[agent_id]
        if section not in options:
            return self.get_default(section, key)
        if key not in options[section]:
            return self.get_default(section, key)
        option = options[section][key]
        if option is None:
            return self.get_default(section, key)
        return option


    @staticmethod
    def extract_system_prompt_extra(final_prompt: str, raw_prompt: str) -> str:
        """Return runtime/plugin additions from the final bridge system prompt.

        ``BridgeContext.system_prompt_raw`` contains the preset prompt before the
        prompt/plugin pipeline, while ``system_prompt`` contains the final value
        after plugins (including late runtime additions such as Real Time and
        Files I/O).  Agent providers with their own internal prompts must receive
        only those additions, otherwise the preset/base prompt would be duplicated.
        """
        final = str(final_prompt or "").strip()
        raw = str(raw_prompt or "").strip()
        if not final or final == raw:
            return ""
        if not raw:
            return final

        idx = final.find(raw)
        if idx >= 0:
            before = final[:idx].strip()
            after = final[idx + len(raw):].strip()
            return "\n\n".join(part for part in (before, after) if part)

        # A plugin may intentionally replace the original prompt (for example a
        # vision prompt in replace mode).  In that case the final prompt is the
        # only authoritative runtime contribution available to nested agents.
        return final

    def get_system_prompt_extra(self, kwargs: Dict[str, Any]) -> str:
        """Return plugin/runtime system-prompt additions for this agent run."""
        if not isinstance(kwargs, dict):
            return ""
        explicit = kwargs.get("system_prompt_extra")
        if explicit is not None:
            return str(explicit or "").strip()

        context = kwargs.get("context")
        final_prompt = kwargs.get("system_prompt", "")
        raw_prompt = ""
        if context is not None:
            if not final_prompt:
                final_prompt = getattr(context, "system_prompt", "")
            raw_prompt = getattr(context, "system_prompt_raw", "")
        return self.extract_system_prompt_extra(final_prompt, raw_prompt)

    def append_system_prompt_extra(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """Append runtime/plugin prompt additions to an agent-specific prompt once."""
        base = str(prompt or "").strip()
        extra = self.get_system_prompt_extra(kwargs)
        if not extra:
            return base
        if extra in base:
            return base
        if not base:
            return extra
        return base + "\n\n" + extra

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