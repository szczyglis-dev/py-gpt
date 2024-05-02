#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

import re

from pygpt_net.core.access.events import ControlEvent
from pygpt_net.utils import trans


class Control:
    def __init__(self, window=None):
        """
        Control handler

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: ControlEvent):
        """
        Handle accessibility event (control)

        :param event: event object
        """
        self.window.core.debug.info("EVENT CTRL: " + event.name)
        # app
        if event.name == ControlEvent.APP_EXIT:
            self.window.close()
        elif event.name == ControlEvent.APP_STATUS:
            status = self.window.core.access.voice.get_status()
            if status != "":
                self.window.controller.audio.read_text(status)

        # camera
        elif event.name == ControlEvent.CAMERA_ENABLE:
            self.window.controller.camera.enable_capture()
        elif event.name == ControlEvent.CAMERA_DISABLE:
            self.window.controller.camera.disable_capture()
        elif event.name == ControlEvent.CAMERA_CAPTURE:
            self.window.controller.camera.manual_capture()

        # ctx
        elif event.name == ControlEvent.CTX_NEW:
            self.window.controller.ctx.new()
        elif event.name == ControlEvent.CTX_PREV:
            self.window.controller.ctx.prev()
        elif event.name == ControlEvent.CTX_NEXT:
            self.window.controller.ctx.next()
        elif event.name == ControlEvent.CTX_LAST:
            self.window.controller.ctx.last()
        elif event.name == ControlEvent.CTX_INPUT_FOCUS:
            self.window.controller.chat.common.focus_input()
            self.handle_result(event, True)
        elif event.name == ControlEvent.CTX_INPUT_CLEAR:
            self.window.controller.chat.input.clear_input()
            self.handle_result(event, True)
        elif event.name == ControlEvent.CTX_STOP:
            self.window.controller.chat.common.stop()
        elif event.name == ControlEvent.CTX_ATTACHMENTS_CLEAR:
            self.window.controller.attachment.clear()
            self.handle_result(event, True)  # TODO event
        elif event.name == ControlEvent.CTX_CURRENT:
            status = self.window.core.access.voice.get_current_ctx()
            if status != "":
                self.window.controller.audio.read_text(status)
        elif event.name == ControlEvent.CTX_READ_LAST:
            text = self.window.core.access.voice.get_last_ctx_item()
            if text != "":
                self.window.controller.audio.read_text(text)
        elif event.name == ControlEvent.CTX_READ_ALL:
            text = self.window.core.access.voice.get_all_ctx_items()
            if text != "":
                self.window.controller.audio.read_text(text)

        # mode
        elif event.name == ControlEvent.MODE_CHAT:
            self.window.controller.mode.set("chat")
            self.handle_result(event, True)
        elif event.name == ControlEvent.MODE_LLAMA_INDEX:
            self.window.controller.mode.se("llama_index")
            self.handle_result(event, True)

        # tabs
        elif event.name == ControlEvent.TAB_NEXT:
            self.window.controller.ui.next_tab()
        elif event.name == ControlEvent.TAB_PREV:
            self.window.controller.ui.prev_tab()

        # tabs: by names
        elif event.name == ControlEvent.TAB_CHAT:
            self.window.controller.ui.switch_tab("chat")
        elif event.name == ControlEvent.TAB_FILES:
            self.window.controller.ui.switch_tab("files")
        elif event.name == ControlEvent.TAB_CALENDAR:
            self.window.controller.ui.switch_tab("calendar")
        elif event.name == ControlEvent.TAB_DRAW:
            self.window.controller.ui.switch_tab("draw")

        # tabs: notepads
        elif event.name == ControlEvent.TAB_NOTEPAD:
            tmp_idx = 1
            if "params" in event.data and event.data["params"] != "":
                try:
                    # regex extract number
                    num = re.findall(r'\d+', event.data["params"])
                    if len(num) > 0:
                        tmp_idx = int(num[0])
                except:
                    pass
            self.window.controller.notepad.switch_to_tab(tmp_idx)
            self.handle_result(event, True)

        # voice control
        elif event.name == ControlEvent.VOICE_COMMAND_START:
            self.window.controller.access.voice.start_recording()
        elif event.name == ControlEvent.VOICE_COMMAND_STOP:
            self.window.controller.access.self.voice.stop_recording()
        elif event.name == ControlEvent.VOICE_COMMAND_TOGGLE:
            self.window.controller.access.self.voice.toggle_recording()

        # voice input
        elif event.name == ControlEvent.VOICE_MESSAGE_START:
            self.window.core.plugins.get("audio_input").handler_simple.start_recording()
        elif event.name == ControlEvent.VOICE_MESSAGE_STOP:
            self.window.core.plugins.get("audio_input").handler_simple.stop_recording()
        elif event.name == ControlEvent.VOICE_MESSAGE_TOGGLE:
            self.window.core.plugins.get("audio_input").handler_simple.toggle_recording()

        # audio enable/disable
        elif event.name == ControlEvent.AUDIO_INPUT_ENABLE:
            self.window.controller.plugins.enable('audio_input')
            self.handle_result(event, True)
        elif event.name == ControlEvent.AUDIO_INPUT_DISABLE:
            self.window.controller.plugins.disable('audio_input')
            self.handle_result(event, True)
        elif event.name == ControlEvent.AUDIO_OUTPUT_ENABLE:
            self.window.controller.plugins.enable('audio_output')
            self.handle_result(event, True)
        elif event.name == ControlEvent.AUDIO_OUTPUT_DISABLE:
            self.window.controller.plugins.disable('audio_output')
            self.handle_result(event, True)

        # input
        elif event.name == ControlEvent.INPUT_SEND:
            if "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.chat.common.clear_input()
                    self.window.controller.chat.common.append_to_input(msg)
                self.window.controller.chat.input.send_input()
        elif event.name == ControlEvent.INPUT_APPEND:
            if "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.chat.common.append_to_input(msg)
                    self.handle_result(event, True)

        # notepad
        elif event.name == ControlEvent.NOTE_ADD:
            if "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    if self.window.controller.notepad.is_active():
                        idx = self.window.controller.notepad.get_current_active()
                        self.window.controller.notepad.append_text(msg, idx)
                    else:
                        self.window.controller.notepad.append_text(msg, 1)
                    self.handle_result(event, True)
        elif event.name == ControlEvent.NOTEPAD_READ:
            if "params" in event.data and event.data["params"] != "":
                idx = 1
                try:
                    # regex extract number
                    num = re.findall(r'\d+', event.data["params"])
                    if len(num) > 0:
                        idx = int(num[0])
                except:
                    pass
                text = self.window.controller.notepad.get_notepad_text(idx)
            else:
                text = self.window.controller.notepad.get_current_notepad_text()
            self.window.controller.audio.read_text(text)

    def handle_result(self, event, result: bool = True):
        """
        Play result

        :param event: event object
        :param result: result
        """
        if not self.window.core.config.get("access.audio.event.speech"):
            return
        key = "event.audio." + event.name
        self.window.controller.audio.read_text(trans(key))
