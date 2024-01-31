#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.13 15:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Agent:
    def __init__(self, window=None):
        """
        Agent controller

        :param window: Window instance
        """
        self.window = window
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
        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        self.stop = False
        self.allowed_cmds = [
            "goal_update",
        ]

    def setup(self):
        """Setup agent controller"""
        # restore options
        if self.window.core.config.get('agent.auto_stop'):
            self.window.ui.config['global']['agent.auto_stop'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.auto_stop'].setChecked(False)

        # register hooks
        self.window.ui.add_hook("update.global.agent.iterations", self.hook_update)

        # load config
        self.window.controller.config.apply_value(
            "global",
            "agent.iterations",
            self.options["agent.iterations"],
            self.window.core.config.get('agent.iterations'),
        )

    def hook_update(self, key, value, caller, *args, **kwargs):
        """
        Hook: on settings update

        :param key: config key
        :param value: config value
        :param caller: caller name
        :param args: args
        :param kwargs: kwargs
        """
        if self.window.core.config.get(key) == value:
            return

        if key == 'agent.iterations':
            self.window.core.config.set(key, value)
            self.window.core.config.save()
            self.update()

    def on_system_prompt(
            self,
            prompt: str,
            append_prompt: str = "",
            auto_stop: bool = True,
    ) -> str:
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :param append_prompt: extra prompt (instruction)
        :param auto_stop: auto stop
        :return: updated prompt
        """
        stop_cmd = ""
        if auto_stop:
            stop_cmd = '\n\nON FINISH: When you believe that the task has been completed 100% and all goals have ' \
                       'been achieved, include the following command in your response, which will stop further ' \
                       'conversation. Remember to put it in the form as given, at the end of response and including ' \
                       'the surrounding ~###~ marks: ~###~{"cmd": "goal_update", "params": {"status": "finished"}}~###~'

        # select prompt to use
        if append_prompt is not None and append_prompt.strip() != "":
            append_prompt = "\n" + append_prompt
        prompt += str(append_prompt) + stop_cmd
        return prompt

    def on_input_before(self, prompt: str) -> str:
        """
        Event: On user input before

        :param prompt: prompt
        :return: updated prompt
        """
        if not self.is_user:
            return prompt

        return "user: " + prompt

    def on_user_send(self, text: str):
        """
        Event: On user send text

        :param text: text
        """
        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        if self.stop:
            self.stop = False
        self.update()  # update status

    def on_ctx_end(
            self,
            ctx: CtxItem,
            iterations: int = 0,
    ):
        """
        Event: On context end

        :param ctx: CtxItem
        :param iterations: iterations
        """
        if self.stop:
            self.stop = False
            self.iteration = 0
            self.prev_output = None
            self.update()  # update status

        if iterations == 0 or self.iteration < int(iterations):
            self.iteration += 1
            self.update()  # update status
            if self.prev_output is not None and self.prev_output != "":
                self.window.controller.chat.input.send(
                    self.prev_output,
                    force=True,
                    internal=True,
                )
                # internal call will not trigger async mode and will hide the message from previous iteration

    def on_ctx_before(
            self,
            ctx: CtxItem,
            reverse_roles: bool = False,
    ):
        """
        Event: Before ctx

        :param ctx: CtxItem
        :param reverse_roles: reverse roles
        """
        ctx.internal = True  # always force internal call
        self.is_user = False
        if self.iteration == 0:
            ctx.first = True

        # reverse roles in ctx
        if self.iteration > 0 \
                and self.iteration % 2 != 0 \
                and reverse_roles:
            tmp_input_name = ctx.input_name
            tmp_output_name = ctx.output_name
            ctx.input_name = tmp_output_name
            ctx.output_name = tmp_input_name

    def on_ctx_after(self, ctx: CtxItem):
        """
        Event: After ctx

        :param ctx: CtxItem
        """
        self.prev_output = ctx.output

    def on_cmd(
            self,
            ctx: CtxItem,
            cmds: list,
    ):
        """
        Event: On commands

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        if self.window.core.config.get('agent.auto_stop'):
            self.cmd(ctx, cmds)

    def cmd(
            self,
            ctx: CtxItem,
            cmds: list,
    ):
        """
        Event: On command

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        for item in my_commands:
            try:
                if item["cmd"] == "goal_update":
                    if item["params"]["status"] == "finished":
                        self.on_stop()
                        self.window.ui.status(trans('status.finished'))  # show info
            except Exception as e:
                self.window.core.debug.error(e)
                return

    def on_stop(self):
        """
        Event: On force stop
        """
        self.iteration = 0
        self.prev_output = None
        self.stop = True

    def on_enable(self):
        """Event: On enable"""
        self.show_status()

    def on_disable(self):
        """Event: On disable"""
        mode = self.window.core.config.get('mode')
        if mode == 'agent' or self.window.controller.plugins.is_type_enabled("agent"):
            return
        self.hide_status()

    def toggle_status(self):
        """Toggle agent status"""
        mode = self.window.core.config.get('mode')
        if mode == 'agent' or self.window.controller.plugins.is_type_enabled("agent"):
            self.show_status()
        else:
            self.hide_status()

    def enable_auto_stop(self):
        """Enable auto stop"""
        self.window.core.config.set('agent.auto_stop', True)
        self.window.core.config.save()

    def disable_auto_stop(self):
        """Disable auto stop"""
        self.window.core.config.set('agent.auto_stop', False)
        self.window.core.config.save()

    def update(self):
        """Update agent status"""
        iterations = "-"
        mode = self.window.core.config.get('mode')

        if mode == "agent":
            iterations = int(self.window.core.config.get("agent.iterations"))
        elif self.window.controller.plugins.is_type_enabled("agent"):
            if self.window.controller.plugins.is_enabled("self_loop"):
                iterations = int(self.window.core.plugins.get_option("self_loop", "iterations"))

        if iterations == 0:
            iterations_str = "∞"
        else:
            iterations_str = str(iterations)

        status = str(self.iteration) + " / " + iterations_str
        self.window.ui.nodes['status_prepend'].setText(status)
        self.toggle_status()

    def show_status(self):
        """Show agent status"""
        self.window.ui.nodes['status_prepend'].setVisible(True)

    def hide_status(self):
        """Hide agent status"""
        self.window.ui.nodes['status_prepend'].setVisible(False)

    def toggle_auto_stop(self, state: bool):
        """
        Toggle auto stop

        :param state: state of checkbox
        """
        if not state:
            self.disable_auto_stop()
        else:
            self.enable_auto_stop()
