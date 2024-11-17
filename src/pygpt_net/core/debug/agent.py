#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

class AgentDebug:
    def __init__(self, window=None):
        """
        Agent debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'agent'

    def update(self):
        """Update debug window"""
        self.window.core.debug.begin(self.id)
        self.window.core.debug.add(self.id, '[Llama-index]', '')
        self.window.core.debug.add(self.id, 'agents', str(self.window.core.agents.provider.get_ids()))
        self.window.core.debug.add(self.id, 'eval_step', str(self.window.controller.agent.llama.eval_step))
        self.window.core.debug.add(self.id, '[LEGACY]', '')
        self.window.core.debug.add(self.id, 'iteration', str(self.window.controller.agent.flow.iteration))
        self.window.core.debug.add(self.id, 'limit', str(self.window.core.config.get("agent.iterations")))
        self.window.core.debug.add(self.id, 'prev_output', str(self.window.controller.agent.flow.prev_output))
        self.window.core.debug.add(self.id, 'is_user', str(self.window.controller.agent.flow.is_user))
        self.window.core.debug.add(self.id, 'stop', str(self.window.controller.agent.flow.stop))
        self.window.core.debug.add(self.id, 'finished', str(self.window.controller.agent.flow.finished))
        self.window.core.debug.add(self.id, 'allowed_cmds', str(self.window.controller.agent.flow.allowed_cmds))

        self.window.core.debug.end(self.id)
