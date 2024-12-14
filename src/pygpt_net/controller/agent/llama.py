#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Any

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Llama:
    def __init__(self, window=None):
        """
        Agents (Llama-index) controller

        :param window: Window instance
        """
        self.window = window
        self.eval_step = 0
        self.options = {
            "agent.llama.loop.score": {
                "type": "int",
                "slider": True,
                "label": "agent.llama.loop.score",
                "min": 0,
                "max": 100,
                "step": 1,
                "value": 75,
                "multiplier": 1,
            },
        }

    def setup(self):
        """Setup agent controller"""
        # register hooks
        self.window.ui.add_hook("update.global.agent.llama.loop.score", self.hook_update)
        self.reload()  # restore config

    def reload(self):
        """Reload agent toolbox options"""
        # loop enable checkbox
        if self.window.core.config.get('agent.llama.loop.enabled'):
            self.window.ui.config['global']['agent.llama.loop.enabled'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.llama.loop.enabled'].setChecked(False)

        # loop score slider
        self.window.controller.config.apply_value(
            parent_id="global",
            key="agent.llama.loop.score",
            option=self.options["agent.llama.loop.score"],
            value=self.window.core.config.get('agent.llama.loop.score'),
        )

    def reset_eval_step(self):
        """Reset evaluation step"""
        self.eval_step = 0

    def eval_step_next(self):
        """Next evaluation step"""
        self.eval_step += 1

    def get_eval_step(self) -> int:
        """
        Get evaluation step

        :return: evaluation step
        """
        return self.eval_step

    def on_user_send(self, text: str):
        """
        Run begin

        :param text: user input
        """
        self.reset_eval_step()  # reset evaluation step

    def on_end(self):
        """End of run"""
        self.eval_step = 0  # reset evaluation step
        if self.window.core.config.get("agent.goal.notify"):
            self.window.ui.tray.show_msg(
                trans("notify.agent.goal.title"),
                trans("notify.agent.goal.content"),
            )

    def on_finish(self, ctx: CtxItem):
        """
        Finish agent run

        :param ctx: CtxItem
        """
        if not self.window.core.config.get("agent.llama.loop.enabled"):
            self.on_end()
            return  # abort if loop is disabled

        # check if not stopped
        if self.window.controller.kernel.stopped():
            self.on_end()
            return

        # check max steps
        max_steps = int(self.window.core.config.get("agent.llama.max_eval"))
        if max_steps != 0 and self.get_eval_step() >= max_steps:
            self.on_end()
            return  # abort if max steps reached

        # evaluation step++
        self.eval_step_next()

        context = BridgeContext()
        context.ctx = ctx
        context.history = self.window.core.ctx.all(meta_id=ctx.meta.id)
        self.window.update_status(trans('status.evaluating'))  # show info
        event = KernelEvent(KernelEvent.REQUEST_NEXT, {
            'context': context,
            'extra': {},
        })
        self.window.dispatch(event)

    def on_stop(self):
        """Stop agent"""
        pass

    def update(self):
        """Update agent status"""
        pass

    def hook_update(self, key: str, value: Any, caller, *args, **kwargs):
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
        if key == 'agent.llama.loop.score':
            self.window.core.config.set(key, int(value))
            self.window.core.config.save()
            self.update()