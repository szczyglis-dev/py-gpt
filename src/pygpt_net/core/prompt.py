#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.12 06:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event


class Prompt:
    def __init__(self, window=None):
        """
        Prompt core

        :param window: Window instance
        """
        self.window = window

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
            # cmd prompt
            if prompt.strip() != "":
                prompt += "\n\n"
            prompt += self.window.core.command.get_prompt()

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
