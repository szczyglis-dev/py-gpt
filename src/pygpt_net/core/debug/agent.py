#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
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
        debug = self.window.core.debug
        agents_provider = self.window.core.agents.provider
        agent_controller = self.window.controller.agent
        agent_legacy = agent_controller.legacy
        agent_config = self.window.core.config

        debug.begin(self.id)
        debug.add(self.id, '[Llama-index]', '')
        debug.add(self.id, 'agents', str(agents_provider.get_ids()))
        debug.add(self.id, 'eval_step', str(agent_controller.llama.eval_step))
        debug.add(self.id, '[LEGACY]', '')
        debug.add(self.id, 'iteration', str(agent_legacy.iteration))
        debug.add(self.id, 'limit', str(agent_config.get("agent.iterations")))
        debug.add(self.id, 'prev_output', str(agent_legacy.prev_output))
        debug.add(self.id, 'is_user', str(agent_legacy.is_user))
        debug.add(self.id, 'stop', str(agent_legacy.stop))
        debug.add(self.id, 'finished', str(agent_legacy.finished))
        debug.add(self.id, 'allowed_cmds', str(agent_legacy.allowed_cmds))
        debug.end(self.id)
