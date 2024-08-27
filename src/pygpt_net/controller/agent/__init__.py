#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 19:00:00                  #
# ================================================== #

from .common import Common
from .experts import Experts
from .flow import Flow


class Agent:
    def __init__(self, window=None):
        """
        Agent controller

        :param window: Window instance
        """
        self.window = window
        self.common = Common(window)
        self.experts = Experts(window)
        self.flow = Flow(window)
        self.options = {
            "agent.iterations": {
                "type": "int",
                "slider": True,
                "label": "agent.iterations",
                "min": 0,
                "max": 100,
                "step": 1,
                "value": 3,
                "multiplier": 1,
            },
        }

    def setup(self):
        """Setup agent controller"""
        # register hooks
        self.window.ui.add_hook("update.global.agent.iterations", self.hook_update)

        # restore config
        self.reload()

    def update(self):
        """Update agent status"""
        iterations = "-"
        mode = self.window.core.config.get('mode')

        # get iterations from plugin or from agent mode
        if mode == "agent":
            iterations = int(self.window.core.config.get("agent.iterations"))
        elif self.is_inline():
            if self.window.controller.plugins.is_enabled("agent"):
                iterations = int(self.window.core.plugins.get_option("agent", "iterations"))
        if iterations == 0:
            iterations_str = "∞"  # infinity loop
        else:
            iterations_str = str(iterations)

        status = str(self.flow.iteration) + " / " + iterations_str
        self.window.ui.nodes['status.agent'].setText(status)
        self.common.toggle_status()

    def reload(self):
        """Reload agent toolbox options"""
        # auto-stop
        if self.window.core.config.get('agent.auto_stop'):
            self.window.ui.config['global']['agent.auto_stop'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.auto_stop'].setChecked(False)

        # continuous
        if self.window.core.config.get('agent.continue.always'):
            self.window.ui.config['global']['agent.continue'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.continue'].setChecked(False)

        # iterations
        self.window.controller.config.apply_value(
            parent_id="global",
            key="agent.iterations",
            option=self.options["agent.iterations"],
            value=self.window.core.config.get('agent.iterations'),
        )

    def hook_update(self, key, value, caller, *args, **kwargs):
        """
        Hook: on option update

        :param key: config key
        :param value: config value
        :param caller: caller name
        :param args: args
        :param kwargs: kwargs
        """
        if self.window.core.config.get(key) == value:
            return

        if key == 'agent.iterations':
            self.window.core.config.set(key, int(value))  # cast to int, if from text input
            self.window.core.config.save()
            self.update()

    def is_inline(self) -> bool:
        """
        Is agent inline (plugin) enabled

        :return: True if enabled
        """
        return self.window.controller.plugins.is_type_enabled("agent")

    def enabled(self) -> bool:
        """
        Is agent enabled

        :return: True if enabled
        """
        return self.window.core.config.get('mode') == 'agent' or self.is_inline()

    def add_run(self):
        """Increment agent iteration"""
        self.flow.iteration += 1

    def stop(self):
        """Stop agent"""
        self.flow.on_stop()
