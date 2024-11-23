#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.23 00:00:00                  #
# ================================================== #

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import Event, AppEvent, KernelEvent, RenderEvent
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_IMAGE,
)
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input controller

        :param window: Window instance
        """
        self.window = window
        self.locked = False
        self.stop = False
        self.generating = False
        self.no_ctx_idx_modes = [
            # MODE_IMAGE,
            MODE_ASSISTANT,
            # MODE_LLAMA_INDEX,
            MODE_AGENT,
        ]  # assistant is handled in async, agent is handled in agent flow
        self.stop_commands = [
            "stop",
            "halt",
        ]

    def send_input(self, force: bool = False):
        """
        Send text from user input (called from UI)

        :param force: force send
        """
        self.window.controller.agent.experts.unlock()  # unlock experts
        self.window.controller.agent.llama.reset_eval_step()  # reset evaluation steps

        # get text from input
        text = self.window.ui.nodes['input'].toPlainText().strip()
        mode = self.window.core.config.get('mode')

        if not force:
            self.window.dispatch(AppEvent(AppEvent.INPUT_SENT))  # app event

            # check if not in edit mode
            if self.window.controller.ctx.extra.is_editing():
                self.window.controller.ctx.extra.edit_submit()
                return

            # if agent mode: iterations check, show alert confirm if infinity loop
            if self.window.controller.agent.common.is_infinity_loop(mode):
                self.window.controller.agent.common.display_infinity_loop_confirm()
                return

        # listen for stop command
        if self.generating \
                and text is not None \
                and text.lower().strip() in self.stop_commands:
            self.window.controller.kernel.stop()  # TODO: to chat main
            self.window.dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))
            return

        # agent modes
        if mode == MODE_AGENT:
            self.window.controller.agent.legacy.on_user_send(text)  # begin legacy agent flow
        elif mode == MODE_AGENT_LLAMA:
            self.window.controller.agent.llama.on_user_send(text)  # begin llama agent flow

        # event: user input send (manually)
        event = Event(Event.USER_SEND, {
            'value': text,
        })
        self.window.dispatch(Event(Event.USER_SEND, {
            'value': text,
        }))
        text = event.data['value']

        # handle attachments with additional context (not images here)
        if mode != MODE_ASSISTANT and self.window.controller.chat.attachment.has(mode):
            self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
                "id": "chat",
                "msg": "Reading attachments..."
            }))
            try:
                self.window.controller.chat.attachment.handle(mode, text)
                return  # return here, will be handled in signal
            except Exception as e:
                self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                    "id": "chat",
                    "msg": "Error reading attachments: {}".format(str(e))
                }))
                return

        # event: handle input
        context = BridgeContext()
        context.prompt = text
        event = KernelEvent(KernelEvent.INPUT_USER, {
            'context': context,
            'extra': {},
        })
        self.window.dispatch(event)

    def send(
            self,
            context: BridgeContext,
            extra: dict,
    ):
        """
        Send input wrapper

        :param context: bridge context
        :param extra: extra data
        """
        text = str(context.prompt)
        prev_ctx = context.ctx
        force = extra.get("force", False)
        reply = extra.get("reply", False)
        internal = extra.get("internal", False)
        parent_id = extra.get("parent_id", None)
        self.execute(
            text=text,
            force=force,
            reply=reply,
            internal=internal,
            prev_ctx=prev_ctx,
            parent_id=parent_id,
        )

    def execute(
            self,
            text: str = None,
            force: bool = False,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: CtxItem = None,
            parent_id: int = None,
    ):
        """
        Execute send input text to API

        :param text: input text
        :param force: force send (ignore input lock)
        :param reply: reply mode (from plugins)
        :param internal: internal call
        :param prev_ctx: previous context (if reply)
        :param parent_id: parent id (if expert)
        """
        self.window.dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "chat",
        }))

        # check if input is not locked
        if self.locked and not force and not internal:
            return

        self.log("Begin.")
        self.generating = True  # set generating flag

        mode = self.window.core.config.get('mode')
        if mode == MODE_ASSISTANT:
            # check if assistant is selected
            if self.window.core.config.get('assistant') is None \
                    or self.window.core.config.get('assistant') == "":
                self.window.ui.dialogs.alert(trans('error.assistant_not_selected'))
                self.generating = False  # unlock
                return
        elif self.window.controller.ui.vision.has_vision():
            # handle auto capture
            self.window.controller.camera.handle_auto_capture()

        # unlock Assistants run thread if locked
        self.window.controller.assistant.threads.stop = False
        self.window.controller.kernel.resume()

        self.log("Input prompt: {}".format(text))  # log

        # agent mode
        if mode == MODE_AGENT:
            self.log("Agent: input before: {}".format(text))
            text = self.window.controller.agent.legacy.on_input_before(text)

        # event: before input
        event = Event(Event.INPUT_BEFORE, {
            'value': text,
            'mode': mode,
        })
        self.window.dispatch(event)
        text = event.data['value']

        # check if image captured from camera, # check if attachment exists
        camera_captured = (self.window.controller.ui.vision.has_vision()
                           and self.window.controller.attachment.has(mode))

        # allow empty input only for vision modes, otherwise abort
        if len(text.strip()) == 0 and not camera_captured:
            self.generating = False  # unlock as not generating
            return

        # check API key, show monit if no API key
        if mode not in self.window.controller.launcher.no_api_key_allowed:
            if not self.window.controller.chat.common.check_api_key():
                self.generating = False
                self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                    "id": "chat",
                }))
                return

        # set state to: busy
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "chat",
            "msg": trans('status.sending'),
        }))

        # clear input field if clear-on-send is enabled
        if self.window.core.config.get('send_clear') and not force and not internal:
            self.window.dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))

        # prepare ctx, create new ctx meta if there is no ctx, or no ctx selected
        if self.window.core.ctx.count_meta() == 0 or self.window.core.ctx.get_current() is None:
            self.window.core.ctx.new()
            self.window.controller.ctx.update()
            self.log("New context created...")  # log
        else:
            # check if current ctx is allowed for this mode - if not, then auto-create new ctx
            self.window.controller.ctx.handle_allowed(mode)

        # send input to API
        if mode == MODE_IMAGE:
            self.window.controller.chat.image.send(
                text=text,
                prev_ctx=prev_ctx,
                parent_id=parent_id,
            )  # image mode
        else:
            # async
            self.window.controller.chat.text.send(
                text=text,
                reply=reply,
                internal=internal,
                prev_ctx=prev_ctx,
                parent_id=parent_id,
            )  # text mode: OpenAI, Langchain, Llama, etc.

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.controller.chat.log(data)
