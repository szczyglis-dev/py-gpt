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

from typing import Optional, Any, Dict

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.bridge.context import MultimodalContext
from pygpt_net.core.events import Event, AppEvent, KernelEvent, RenderEvent
from pygpt_net.core.types import (
    MODE_AGENT,
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
        dispatch = self.window.dispatch
        mode = self.window.core.config.get('mode')
        event = Event(Event.INPUT_BEGIN, {
            'mode': mode,
            'force': force,
            'stop': False,
        })
        dispatch(event)
        stop = event.data.get('stop', False)

        # get text from input
        text = self.window.ui.nodes['input'].toPlainText().strip()

        if not force:
            dispatch(AppEvent(AppEvent.INPUT_SENT))  # app event
            if stop:
                return

        # listen for stop command
        if self.generating \
                and text is not None \
                and text.lower().strip() in self.stop_commands:
            self.window.controller.kernel.stop()  # TODO: to chat main
            dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))
            return

        # event: user input send (manually)
        event = Event(Event.USER_SEND, {
            'mode': mode,
            'value': text,
        })
        dispatch(event)
        text = event.data['value']

        # if attachments, return here - send will be handled via signal after upload
        if self.handle_attachment(mode, text):
            return

        # kernel event: handle input
        context = BridgeContext()
        context.prompt = text
        dispatch(KernelEvent(KernelEvent.INPUT_USER, {
            'context': context,
            'extra': {},
        }))

    def send(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
    ):
        """
        Send input wrapper

        :param context: bridge context
        :param extra: extra data
        """
        self.execute(
            text=str(context.prompt),
            force=extra.get("force", False),
            reply=extra.get("reply", False),
            internal=extra.get("internal", False),
            prev_ctx=context.ctx,
            multimodal_ctx=context.multimodal_ctx,
        )

    def execute(
            self,
            text: str,
            force: bool = False,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: Optional[CtxItem] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
    ):
        """
        Execute send input text to API

        :param text: input text
        :param force: force send (ignore input lock)
        :param reply: reply mode (from plugins)
        :param internal: internal call
        :param prev_ctx: previous context (if reply)
        :param multimodal_ctx: multimodal context
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        log = controller.chat.log

        dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "chat",
        }))

        # check if input is not locked
        if self.locked and not force and not internal:
            return

        log("Begin.")
        self.generating = True  # set generating flag

        # check if assistant is selected
        mode = core.config.get('mode')
        if mode == MODE_ASSISTANT:
            if not controller.assistant.check():
                self.generating = False  # unlock
                return

        # handle camera capture
        controller.camera.handle_auto_capture(mode)

        # unlock if locked
        controller.assistant.resume()
        controller.kernel.resume()

        log(f"Input prompt: {text}")  # log

        # event: before input handle
        event = Event(Event.INPUT_BEFORE, {
            'mode': mode,
            'value': text,
            'multimodal_ctx': multimodal_ctx,
            'stop': False,
            'silent': False,  # silent mode (without error messages)
        })
        dispatch(event)
        text = event.data['value']
        stop = event.data.get('stop', False)
        silent = event.data.get('silent', False)

        if stop:  # abort via event
            self.generating = False
            if not silent:
                dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                    "id": "chat",
                }))
            return

        # set state to: busy
        dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
            "id": "chat",
            "msg": trans('status.sending'),
        }))

        # clear input field if clear-on-send is enabled
        if core.config.get('send_clear') and not force and not internal:
            dispatch(RenderEvent(RenderEvent.CLEAR_INPUT))

        # create ctx, handle allowed, etc.
        dispatch(Event(Event.INPUT_ACCEPT, {
            'value': text,
            'multimodal_ctx': multimodal_ctx,
            'mode': mode,
        }))

        # send input to API
        if mode == MODE_IMAGE:
            controller.chat.image.send(
                text=text,
                prev_ctx=prev_ctx,
            )  # image generation
        else:
            controller.chat.text.send(
                text=text,
                reply=reply,
                internal=internal,
                prev_ctx=prev_ctx,
                multimodal_ctx=multimodal_ctx,
            )  # text mode: OpenAI, LlamaIndex, etc.

    def handle_attachment(self, mode: str, text: str) -> bool:
        """
        Handle attachments with additional context (not images here)

        :param mode: Mode (e.g., MODE_ASSISTANT, MODE_CHAT)
        :param text: Input text
        :return: bool: True if attachments exists, False otherwise
        """
        controller = self.window.controller
        dispatch = self.window.dispatch
        exists = False

        # handle attachments with additional context (not images here)
        if mode != MODE_ASSISTANT and controller.chat.attachment.has(mode):
            exists = True
            dispatch(KernelEvent(KernelEvent.STATE_BUSY, {
                "id": "chat",
                "msg": "Reading attachments..."
            }))
            try:
                controller.chat.attachment.handle(mode, text)
            except Exception as e:
                dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                    "id": "chat",
                    "msg": f"Error reading attachments: {e}"
                }))

        return exists
