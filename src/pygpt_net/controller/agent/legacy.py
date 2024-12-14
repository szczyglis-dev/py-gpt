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

from typing import Optional, List, Dict, Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
)
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Legacy:
    def __init__(self, window=None):
        """
        Agent flow controller

        :param window: Window instance
        """
        self.window = window
        self.iteration = 0  # legacy
        self.prev_output = None
        self.is_user = True
        self.stop = False
        self.finished = False
        self.allowed_cmds = [
            "goal_update",
        ]
        self.pause_status = ["pause", "failed", "wait"]
        self.prompt_goal_native = """
        STATUS UPDATE: You can use "goal_update" command to update status of the task. 
        ON GOAL FINISH: When you believe that the task has been completed 100% and all goals have been achieved, 
        run "goal_update" command with status = "finished".
        ON PAUSE, FAILED OR WAIT: If more data from user is needed to achieve the goal or task run must be paused 
        or task was failed or when the conversation falls into a loop, THEN STOP REASONING and include "goal_update" 
        command with one of these statuses: "pause", "failed" or "wait".
        """
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
        self.reload()  # restore config

    def reload(self):
        """Reload agent toolbox options"""
        # auto-stop checkbox
        if self.window.core.config.get('agent.auto_stop'):
            self.window.ui.config['global']['agent.auto_stop'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.auto_stop'].setChecked(False)

        # continuous mode checkbox
        if self.window.core.config.get('agent.continue.always'):
            self.window.ui.config['global']['agent.continue'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.continue'].setChecked(False)

        # iterations slider
        self.window.controller.config.apply_value(
            parent_id="global",
            key="agent.iterations",
            option=self.options["agent.iterations"],
            value=self.window.core.config.get('agent.iterations'),
        )

    def update(self):
        """Update agent status"""
        iterations = "-"
        mode = self.window.core.config.get('mode')

        # get iterations from plugin or from agent mode
        if mode in [
            MODE_AGENT,
            MODE_AGENT_LLAMA,
        ]:
            iterations = int(self.window.core.config.get("agent.iterations"))
        elif self.is_inline():
            if self.window.controller.plugins.is_enabled("agent"):
                iterations = int(self.window.core.plugins.get_option("agent", "iterations"))
        if iterations == 0:
            iterations_str = "∞"  # infinity loop
        else:
            iterations_str = str(iterations)

        status = str(self.iteration) + " / " + iterations_str
        self.window.ui.nodes['status.agent'].setText(status)
        self.window.controller.agent.common.toggle_status()

    def get_functions(self) -> List[Dict[str, Any]]:
        """
        Append goal commands

        :return: goal commands
        """
        cmds = [
            {
                "cmd": "goal_update",
                "instruction": "Update goal status",
                "params": [
                    {
                        "name": "status",
                        "description": "status to update",
                        "required": True,
                        "type": "str",
                        "enum": {
                            "status": ["finished", "pause", "failed", "wait"],
                        }
                    }
                ]
            }
        ]
        return cmds

    def on_system_prompt(
            self,
            prompt: str,
            append_prompt: Optional[str] = "",
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
            if not self.window.core.command.is_native_enabled():
                stop_cmd = "\n\n" + self.window.core.prompt.get("agent.goal")  # use ### commands
            else:
                stop_cmd = "\n\n" + self.prompt_goal_native  # use API native functions
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

        return "user: " + prompt  # add user prefix

    def on_user_send(self, text: str):
        """
        Event: On user send text

        :param text: text
        """
        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        self.finished = False  # reset finished flag
        if self.stop:
            self.stop = False
        self.window.controller.agent.legacy.update()  # update status

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
            return

        # if ctx has commands to execute then abort sending reply (command response will be sent)
        reply_abort = False
        if len(ctx.cmds) > 0:
            reply_abort = True
            # exception for expert_call command
            if len(ctx.cmds) == 1 and ctx.cmds[0]["cmd"] == "expert_call":
                reply_abort = False
            # if commands execution is disabled, then don't abort (there is no command response)
            if not self.window.core.config.get("cmd"):
                reply_abort = False
        if reply_abort:
            return

        if iterations == 0 or self.iteration < int(iterations):
            self.iteration += 1
            self.window.controller.agent.legacy.update()  # update status
            if self.prev_output is not None and self.prev_output != "":

                # always abort if already waiting for reply from expert or command
                if not self.window.controller.kernel.stack.waiting():
                    # add to reply stack
                    reply = ReplyContext()
                    reply.type = ReplyContext.AGENT_CONTINUE
                    reply.ctx = ctx
                    reply.input = self.prev_output
                    # send to kernel
                    context = BridgeContext()
                    context.ctx = ctx
                    context.reply_context = reply
                    event = KernelEvent(KernelEvent.AGENT_CONTINUE, {
                        'context': context,
                        'extra': {},
                    })
                    self.window.dispatch(event)

        # internal call will not trigger async mode and will hide the message from previous iteration
        elif self.iteration >= int(iterations):
            self.on_stop(auto=True)
            if self.window.core.config.get("agent.goal.notify"):
                self.window.ui.tray.show_msg(
                    trans("notify.agent.stop.title"),
                    trans("notify.agent.stop.content"),
                )

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
        self.prev_output = self.window.core.prompt.get("agent.continue")  # continue if needed...
        if self.window.core.config.get('agent.continue.always'):
            self.prev_output = self.window.core.prompt.get("agent.continue.always")  # continue reasoning...
        if ctx.extra_ctx is not None and ctx.extra_ctx != "":
            self.prev_output = ctx.extra_ctx

    def on_cmd(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]],
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
            cmds: List[Dict[str, Any]],
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
                        self.on_stop(auto=True)
                        self.window.update_status(trans('status.finished'))  # show info
                        self.finished = True
                        if self.window.core.config.get("agent.goal.notify"):
                            self.window.ui.tray.show_msg(
                                trans("notify.agent.goal.title"),
                                trans("notify.agent.goal.content"),
                            )
                    elif item["params"]["status"] in self.pause_status:
                        self.on_stop(auto=True)
                        self.window.update_status(trans('status.finished'))  # show info
                        self.finished = True
            except Exception as e:
                self.window.core.debug.error(e)
                return

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
        return self.window.core.config.get('mode') == MODE_AGENT or self.is_inline()

    def add_run(self):
        """Increment agent iteration"""
        self.iteration += 1

    def on_stop(self, auto: bool = False):
        """
        Event: On force stop

        :param auto: auto
        """
        self.window.controller.kernel.stack.lock()
        self.window.controller.chat.common.unlock_input()
        self.iteration = 0
        self.prev_output = None
        self.stop = True
        self.finished = False  # reset finished flag

        # update index if auto-index enabled
        if auto:
            self.window.controller.idx.on_ctx_end(
                ctx=None,
                mode="agent",
            )

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
        if key == 'agent.iterations':
            self.window.core.config.set(key, int(value))  # cast to int, if from text input
            self.window.core.config.save()
            self.update()
