#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
# ================================================== #

from pygpt_net.core.events import BaseEvent, Event
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .common import Common
from .experts import Experts
from .legacy import Legacy
from .llama import Llama

class Agent:
    def __init__(self, window=None):
        """
        Agents controller

        :param window: Window instance
        """
        self.window = window
        self.common = Common(window)
        self.experts = Experts(window)
        self.llama = Llama(window)
        self.legacy = Legacy(window)

    def setup(self):
        """Setup agents"""
        self.legacy.setup()
        self.llama.setup()

    def reload(self):
        """Reload agent toolbox options"""
        self.legacy.reload()
        self.llama.reload()

    def stop(self):
        """Force stop all agents"""
        self.legacy.on_stop()
        self.llama.on_stop()

    def handle(self, event: BaseEvent):
        """
        Handle events

        :param event: BaseEvent: Event to handle
        """
        name = event.name

        # on input begin, unlock experts and reset evaluation steps
        if name == Event.INPUT_BEGIN:
            mode = event.data.get("mode", "")
            force = event.data.get("force", False)
            self.experts.unlock()  # unlock experts
            self.llama.reset_eval_step()  # reset evaluation steps

            if not force:
                # if agent mode: iterations check, show alert confirm if infinity loop
                if self.common.is_infinity_loop(mode):
                    event.data["stop"] = True  # stop flow
                    self.common.display_infinity_loop_confirm()
                    return

                # check if agent is selected
                if mode in (MODE_AGENT_OPENAI, MODE_AGENT_LLAMA):
                    preset = self.window.controller.presets.get_current()
                    if not preset or preset.name == "*":
                        event.data["stop"] = True  # stop flow
                        self.window.ui.dialogs.alert(
                            trans("dialog.agent.not_selected"))
                        return

        # on user send, start agent flow
        elif name == Event.USER_SEND:
            mode = event.data.get("mode", "")
            text = event.data.get("value", "")
            if mode == MODE_AGENT:
                self.legacy.on_user_send(text)  # begin Legacy (autonomous) agent flow
            elif mode in (
                    MODE_AGENT_LLAMA,
                    MODE_AGENT_OPENAI,
            ):
                self.llama.on_user_send(text)  # begin LlamaIndex adn OpenAI agent flow

        # on input before, process text before sending input
        elif name == Event.INPUT_BEFORE:
            mode = event.data.get("mode", "")
            if mode == MODE_AGENT:
                text = event.data.get("value", "")
                self.window.controller.chat.log(f"Agent: input before: {text}")
                event.data["value"] = self.legacy.on_input_before(text)

        # on pre-prompt
        elif name == Event.PRE_PROMPT:
            mode = event.data.get("mode", "")
            sys_prompt = event.data.get("value", "")
            is_expert = event.data.get("is_expert", False)
            if is_expert:
                return # abort if expert call
            event.data["value"] = self.experts.append_prompts(
                mode,
                sys_prompt,
            )
        # on ctx after
        elif name == Event.CTX_BEFORE:
            mode = event.data.get("mode", "")
            if mode == MODE_AGENT:
                self.legacy.on_ctx_before(event.ctx)

        # on bridge before, prepare bridge context
        elif name == Event.BRIDGE_BEFORE:
            mode = event.data.get("mode", "")
            bridge_context = event.data.get("context", None)
            extra = event.data.get("extra", {})
            if mode in (MODE_AGENT_LLAMA, MODE_AGENT_OPENAI):

                # agent provider
                agent_provider = None  # agent provider (llama or openai)
                if mode == MODE_AGENT_LLAMA:
                    agent_provider = self.window.core.config.get("agent.llama.provider")
                elif mode == MODE_AGENT_OPENAI:
                    agent_provider =self.window.core.config.get("agent.openai.provider")
                agent_idx = self.window.core.config.get("agent.llama.idx")

                extra["agent_idx"] = agent_idx
                extra["agent_provider"] = agent_provider

                # update assistant ID if assistant agent
                if mode == MODE_AGENT_LLAMA:
                    preset = self.window.controller.presets.get_current()
                    if preset is not None:
                        bridge_context.assistant_id = preset.assistant_id

        # on ctx after
        elif name == Event.CTX_AFTER:
            mode = event.data.get("mode", "")
            if mode == MODE_AGENT:
                self.legacy.on_ctx_after(event.ctx)

        # on ctx end
        elif name == Event.CTX_END:
            mode = event.data.get("mode", "")
            if mode == MODE_AGENT:
                iterations = int(self.window.core.config.get("agent.iterations"))
                self.window.controller.chat.log(f"Agent: ctx end, iterations: {iterations}")
                self.legacy.on_ctx_end(
                    event.ctx,
                    iterations=iterations,
                )

    def on_reply(self, ctx: CtxItem):
        """
        On reply event

        :param ctx: CtxItem: Context item to handle reply for
        """
        if ctx.internal and self.legacy.enabled():
            self.legacy.add_run()
            self.legacy.update()
