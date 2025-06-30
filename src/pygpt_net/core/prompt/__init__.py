#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 20:00:00                  #
# ================================================== #

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from .base import Base
from .custom import Custom
from .template import Template


class Prompt:
    def __init__(self, window=None):
        """
        Prompt core

        :param window: Window instance
        """
        self.window = window
        self.base = Base(window)
        self.custom = Custom(window)
        self.template = Template(window)

    def get(
            self,
            prompt: str,
            mode: str = None,
            model: ModelItem = None
    ) -> str:
        """
        Get system prompt content

        :param prompt: id of the prompt
        :param mode: mode
        :param model: model item
        :return: text content
        """
        return self.base.get(
            prompt=prompt,
            mode=mode,
            model=model,
        )

    def build_final_system_prompt(
            self,
            prompt: str,
            mode: str,
            model: ModelItem = None
    ) -> str:
        """
        Build final system prompt

        :param prompt: prompt
        :param mode: mode
        :param model: model item
        :return: final system prompt
        """
        # tmp dispatch event: system prompt
        event = Event(Event.SYSTEM_PROMPT, {
            'mode': self.window.core.config.get('mode'),
            'value': prompt,
            'silent': True,
        })
        self.window.dispatch(event)
        prompt = event.data['value']

        if (self.window.core.config.get('cmd')
                or self.window.controller.plugins.is_type_enabled("cmd.inline")):

            # abort if native func call enabled
            if self.window.core.command.is_native_enabled():
                return prompt

            # abort if model not supported
            # if not self.window.core.command.is_model_supports_tools(mode, model):
                # return prompt

            # cmd syntax tokens
            data = {
                'prompt': prompt,
                'silent': True,
                'syntax': [],
                'cmd': [],
            }

            # IMPORTANT: append command syntax only if at least one command is detected
            # tmp dispatch event: command syntax apply
            # full execute cmd syntax
            if self.window.core.command.is_cmd_prompt_enabled():
                if self.window.core.config.get('cmd'):
                    event = Event(Event.CMD_SYNTAX, data)
                    self.window.dispatch(event)
                    if event.data and "cmd" in event.data and event.data["cmd"]:
                        prompt = self.window.core.command.append_syntax(
                            data=event.data,
                            mode=mode,
                            model=model,
                        )

                # inline cmd syntax only
                elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
                    event = Event(Event.CMD_SYNTAX_INLINE, data)
                    self.window.dispatch(event)
                    if event.data and "cmd" in event.data and event.data["cmd"]:
                        prompt = self.window.core.command.append_syntax(
                            data=event.data,
                            mode=mode,
                            model=model,
                        )

        return prompt

    def prepare_sys_prompt(
            self,
            mode: str,
            model: ModelItem,
            sys_prompt: str,
            ctx: CtxItem,
            reply: bool,
            internal: bool,
            is_expert: bool = False,
            disable_native_tool_calls: bool = False,
    ) -> str:
        """
        Prepare system prompt

        :param mode: mode
        :param model: model item
        :param sys_prompt: system prompt
        :param ctx: context item
        :param reply: reply from plugins
        :param internal: internal call
        :param is_expert: called from expert
        :param disable_native_tool_calls: True to disable native func calls
        :return: system prompt
        """
        # event: system prompt (append to system prompt)
        event = Event(Event.SYSTEM_PROMPT, {
            'mode': mode,
            'value': sys_prompt,
            'is_expert': is_expert,
        })
        self.window.dispatch(event)
        sys_prompt = event.data['value']

        # event: post prompt (post-handle system prompt)
        event = Event(Event.POST_PROMPT, {
            'mode': mode,
            'reply': reply,
            'internal': internal,
            'value': sys_prompt,
            'is_expert': is_expert,
        })
        event.ctx = ctx
        self.window.dispatch(event)
        sys_prompt = event.data['value']

        # event: command syntax apply (if commands enabled or inline plugin then append commands prompt)
        if self.window.core.config.get('cmd') or self.window.controller.plugins.is_type_enabled("cmd.inline"):
            if self.window.core.command.is_native_enabled() and not disable_native_tool_calls:
                return sys_prompt  # abort if native func call enabled

            # abort if model not supported
            # if not self.window.core.command.is_model_supports_tools(mode, model):
                # return sys_prompt

            data = {
                'mode': mode,
                'prompt': sys_prompt,
                'syntax': [],
                'cmd': [],
                'is_expert': is_expert,
            }
            # IMPORTANT: append command syntax only if at least one command is detected
            # full execute cmd syntax
            if self.window.core.command.is_cmd_prompt_enabled():
                if self.window.core.config.get('cmd'):
                    event = Event(Event.CMD_SYNTAX, data)
                    self.window.dispatch(event)
                    if event.data and "cmd" in event.data and event.data["cmd"]:
                        sys_prompt = self.window.core.command.append_syntax(
                            data=event.data,
                            mode=mode,
                            model=model,
                        )

                # inline cmd syntax only
                elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
                    event = Event(Event.CMD_SYNTAX_INLINE, data)
                    self.window.dispatch(event)
                    if event.data and "cmd" in event.data and event.data["cmd"]:
                        sys_prompt = self.window.core.command.append_syntax(
                            data=event.data,
                            mode=mode,
                            model=model,
                        )

        return sys_prompt
