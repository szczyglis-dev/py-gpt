#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 20:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event

from .template import Template
from ...item.ctx import CtxItem


class Prompt:
    def __init__(self, window=None):
        """
        Prompt core

        :param window: Window instance
        """
        self.window = window
        self.template = Template(window)

    def get(self, prompt: str) -> str:
        """
        Get prompt content

        :param prompt: id of the prompt
        :return: text content
        """
        key = "prompt." + prompt
        if self.window.core.config.has(key):
            return str(self.window.core.config.get(key))
        return ""

    def build_final_system_prompt(self, prompt: str) -> str:
        # tmp dispatch event: system prompt
        event = Event(Event.SYSTEM_PROMPT, {
            'mode': self.window.core.config.get('mode'),
            'value': prompt,
            'silent': True,
        })
        self.window.core.dispatcher.dispatch(event)
        prompt = event.data['value']

        if self.window.core.config.get('cmd') or self.window.controller.plugins.is_type_enabled("cmd.inline"):
            if self.window.core.command.is_native_enabled():
                return prompt  # abort if native func call enabled

            # cmd syntax tokens
            data = {
                'prompt': prompt,
                'silent': True,
                'syntax': [],
                'cmd': [],
            }

            # tmp dispatch event: command syntax apply
            # full execute cmd syntax
            if self.window.core.config.get('cmd'):
                event = Event(Event.CMD_SYNTAX, data)
                self.window.core.dispatcher.dispatch(event)
                prompt = self.window.core.command.append_syntax(event.data)

            # inline cmd syntax only
            elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
                event = Event(Event.CMD_SYNTAX_INLINE, data)
                self.window.core.dispatcher.dispatch(event)
                prompt = self.window.core.command.append_syntax(event.data)

        return prompt

    def prepare_sys_prompt(
            self,
            mode: str,
            sys_prompt: str,
            ctx: CtxItem,
            reply: bool,
            internal: bool,
            is_expert: bool = False
    ):
        """
        Prepare system prompt

        :param mode: mode
        :param sys_prompt: system prompt
        :param ctx: context item
        :param reply: reply from plugins
        :param internal: internal call
        :param is_expert: called from expert
        :return: system prompt
        """
        # event: system prompt (append to system prompt)
        event = Event(Event.SYSTEM_PROMPT, {
            'mode': mode,
            'value': sys_prompt,
            'is_expert': is_expert,
        })
        self.window.core.dispatcher.dispatch(event)
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
        self.window.core.dispatcher.dispatch(event)
        sys_prompt = event.data['value']

        # event: command syntax apply (if commands enabled or inline plugin then append commands prompt)
        if self.window.core.config.get('cmd') or self.window.controller.plugins.is_type_enabled("cmd.inline"):
            if self.window.core.command.is_native_enabled():
                return sys_prompt  # abort if native func call enabled

            data = {
                'mode': mode,
                'prompt': sys_prompt,
                'syntax': [],
                'cmd': [],
                'is_expert': is_expert,
            }
            # full execute cmd syntax
            if self.window.core.config.get('cmd'):
                event = Event(Event.CMD_SYNTAX, data)
                self.window.core.dispatcher.dispatch(event)
                sys_prompt = self.window.core.command.append_syntax(event.data)

            # inline cmd syntax only
            elif self.window.controller.plugins.is_type_enabled("cmd.inline"):
                event = Event(Event.CMD_SYNTAX_INLINE, data)
                self.window.core.dispatcher.dispatch(event)
                sys_prompt = self.window.core.command.append_syntax(event.data)

        return sys_prompt
