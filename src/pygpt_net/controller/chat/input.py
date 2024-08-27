#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 05:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.core.access.events import AppEvent
from pygpt_net.core.dispatcher import Event
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
        self.no_api_key_allowed = [
            "langchain",
            "llama_index",
            "agent",
            "expert",
        ]
        self.no_ctx_idx_modes = [
            # "img",
            "assistant",
            # "llama_index",
            "agent",
        ]  # assistant is handled in async, agent is handled in agent flow

    def send_input(self, force: bool = False):
        """
        Send text from user input (called from UI)

        :param force: force send
        """
        self.window.controller.agent.experts.unlock()  # unlock experts
        if not force:
            self.window.core.dispatcher.dispatch(AppEvent(AppEvent.INPUT_SENT))  # app event

        # check if not in edit mode
        if not force and self.window.controller.ctx.extra.is_editing():
            self.window.controller.ctx.extra.edit_submit()
            return

        # get text from input
        text = self.window.ui.nodes['input'].toPlainText().strip()
        mode = self.window.core.config.get('mode')

        # if agent mode: iterations check
        if not force:
            if (mode == "agent" and self.window.core.config.get('agent.iterations') == 0) \
                    or (self.window.controller.plugins.is_enabled("agent")
                        and self.window.core.plugins.get_option("agent", "iterations") == 0):

                # show alert confirm
                self.window.ui.dialogs.confirm(
                    type="agent.infinity.run",
                    id=0,
                    msg=trans("agent.infinity.confirm.content"),
                )
                return

        if self.generating \
                and text is not None \
                and text.strip() == "stop":
            self.window.controller.chat.common.stop()  # TODO: to chat main
            self.window.controller.chat.render.clear_input()
            return

        # agent mode
        if mode == 'agent':
            self.window.controller.agent.flow.on_user_send(text)

        # event: user input send (manually)
        event = Event(Event.USER_SEND, {
            'value': text,
        })
        self.window.core.dispatcher.dispatch(event)
        text = event.data['value']
        self.send(text)

    def send(
            self,
            text: str = None,
            force: bool = False,
            reply: bool = False,
            internal: bool = False,
            prev_ctx: CtxItem = None,
            parent_id: int = None,
    ):
        """
        Send input wrapper

        :param text: input text
        :param force: force send (ignore input lock)
        :param reply: reply mode (from plugins)
        :param internal: internal call
        :param prev_ctx: previous context (if reply)
        :param parent_id: parent id (if expert)
        """
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
        self.window.stateChanged.emit(self.window.STATE_IDLE)

        # check if input is not locked
        if self.locked and not force and not internal:
            return

        self.log("Begin.")

        self.generating = True  # set generating flag

        mode = self.window.core.config.get('mode')

        if mode == 'assistant':
            # check if assistant is selected
            if self.window.core.config.get('assistant') is None \
                    or self.window.core.config.get('assistant') == "":
                self.window.ui.dialogs.alert(trans('error.assistant_not_selected'))
                self.generating = False  # unlock
                return
        elif (mode == 'vision'
              or self.window.controller.plugins.is_type_enabled('vision')
              or self.window.controller.ui.vision.is_vision_model()):
            # capture frame from camera if auto-capture enabled
            if self.window.controller.camera.is_enabled():
                if self.window.controller.camera.is_auto():
                    self.window.controller.camera.capture_frame(False)
                    self.log("Captured frame from camera.")  # log

        # check if attachment exists, make this here to prevent clearing list on async reply!
        has_attachments = self.window.controller.attachment.has(mode)

        # unlock Assistant run thread if locked
        self.window.controller.assistant.threads.stop = False
        self.stop = False

        self.log("Input prompt: {}".format(text))  # log

        # agent mode
        if mode == 'agent':
            self.log("Agent: input before: {}".format(text))
            text = self.window.controller.agent.flow.on_input_before(text)

        # event: before input
        event = Event(Event.INPUT_BEFORE, {
            'value': text,
            'mode': mode,
        })
        self.window.core.dispatcher.dispatch(event)
        text = event.data['value']

        # check if image captured from camera
        camera_captured = (
                (
                        mode == 'vision'
                        or self.window.controller.plugins.is_type_enabled('vision')
                        or self.window.controller.ui.vision.is_vision_model()
                )
                and self.window.controller.attachment.has(mode)  # check if attachment exists
        )

        # allow empty input only for vision modes, otherwise abort
        if len(text.strip()) == 0 and not camera_captured:
            self.generating = False  # unlock as not generating
            return

        # check API key, show monit if not set
        if mode not in self.no_api_key_allowed:
            if not self.window.controller.chat.common.check_api_key():
                self.generating = False
                self.window.stateChanged.emit(self.window.STATE_ERROR)
                return

        self.window.ui.status(trans('status.sending'))

        # clear input field if clear-on-send is enabled
        if self.window.core.config.get('send_clear') and not force and not internal:
            self.window.controller.chat.render.clear_input()

        # prepare ctx, create new ctx meta if there is no ctx, or no ctx selected
        if self.window.core.ctx.count_meta() == 0 or self.window.core.ctx.current is None:
            self.window.core.ctx.new()
            self.window.controller.ctx.update()
            self.log("New context created...")  # log
        else:
            # check if current ctx is allowed for this mode - if not, then create new ctx
            self.window.controller.ctx.handle_allowed(mode)

        # update UI
        QApplication.processEvents()

        # send input to API, return ctx
        if self.window.core.config.get('mode') == 'img':
            ctx = self.window.controller.chat.image.send(
                text=text,
                prev_ctx=prev_ctx,
                parent_id=parent_id,
            )  # image mode
        else:
            ctx = self.window.controller.chat.text.send(
                text=text,
                reply=reply,
                internal=internal,
                prev_ctx=prev_ctx,
                parent_id=parent_id,
            )  # text mode: OpenAI, Langchain, Llama, etc.

        self.window.controller.chat.output.handle_end(ctx, mode, has_attachments)  # handle end.

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
