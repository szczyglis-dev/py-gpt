#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.21 16:00:00                  #
# ================================================== #

import re

from PySide6.QtCore import QTimer
from pygpt_net.core.access.events import ControlEvent
from pygpt_net.utils import trans


class Control:

    CTX_TIMER_DELAY = 2000  # delay before ctx change execute (ms)
    MODE_TIMER_DELAY = 2000  # delay before mode change execute (ms)

    def __init__(self, window=None):
        """
        Control handler

        :param window: Window instance
        """
        self.window = window
        self.last_confirm = None
        self.ctx_timer = QTimer(self.window)
        self.ctx_timer.timeout.connect(self.handle_ctx)
        self.mode_timer = QTimer(self.window)
        self.mode_timer.timeout.connect(self.handle_mode)
        self.ctx_action = None
        self.mode_action = None

    def handle_ctx(self):
        """Handle context action (delayed)"""
        self.ctx_timer.stop()
        if self.ctx_action is not None:
            if self.ctx_action == ControlEvent.CTX_NEW:
                self.window.controller.ctx.new(force=True)
            elif self.ctx_action == ControlEvent.CTX_PREV:
                self.window.controller.ctx.prev()
            elif self.ctx_action == ControlEvent.CTX_NEXT:
                self.window.controller.ctx.next()
            elif self.ctx_action == ControlEvent.CTX_LAST:
                self.window.controller.ctx.last()
            self.ctx_action = None

    def handle_mode(self):
        """Handle mode action (delayed)"""
        self.mode_timer.stop()
        if self.mode_action is not None:
            if self.mode_action == ControlEvent.MODE_NEXT:
                self.window.controller.mode.next()
            elif self.mode_action == ControlEvent.MODE_PREV:
                self.window.controller.mode.prev()
            elif self.mode_action == ControlEvent.MODE_CHAT:
                self.window.controller.mode.set("chat")
            elif self.mode_action == ControlEvent.MODE_LLAMA_INDEX:
                self.window.controller.mode.set("llama_index")
            self.mode_action = None

    def handle(self, event: ControlEvent, force: bool = False):
        """
        Handle accessibility event (ControlEvent)

        :param event: event object
        :param force: True if force window close on APP_EXIT event
        """
        self.window.core.debug.info("EVENT CTRL: " + event.name)

        # reset last confirm
        if event.name != ControlEvent.CMD_CONFIRM:
            self.last_confirm = None

        # app exit
        if event.name == ControlEvent.APP_EXIT:
            if force:  # if confirmed
                self.window.close()
            else:  # play confirm
                self.last_confirm = event
                self.window.controller.audio.play_event(
                    trans("event.audio.confirm"),
                    event,
                )
            return
        # status changed
        elif event.name == ControlEvent.APP_STATUS:
            status = self.window.core.access.helpers.get_status()
            if status != "":
                self.window.controller.audio.play_event(
                    status,
                    event,
                )

        # unrecognized command (abort)
        if event.name == ControlEvent.VOICE_CONTROL_UNRECOGNIZED:
            self.window.controller.audio.play_event(
                trans("event.audio.voice.control.unrecognized"),
                event,
            )
            return

        # confirm last action
        elif event.name == ControlEvent.CMD_CONFIRM:
            if self.last_confirm is not None:
                self.handle(self.last_confirm, force=True)
                self.last_confirm = None

        # camera
        elif event.name == ControlEvent.CAMERA_ENABLE:
            self.window.controller.camera.enable_capture()
        elif event.name == ControlEvent.CAMERA_DISABLE:
            self.window.controller.camera.disable_capture()
        elif event.name == ControlEvent.CAMERA_CAPTURE:
            self.window.controller.camera.manual_capture()

        # ctx
        elif event.name == ControlEvent.CTX_NEW:
            self.ctx_action = ControlEvent.CTX_NEW
            self.ctx_timer.start(self.CTX_TIMER_DELAY)
        elif event.name == ControlEvent.CTX_PREV:
            self.ctx_action = ControlEvent.CTX_PREV
            self.ctx_timer.start(self.CTX_TIMER_DELAY)
        elif event.name == ControlEvent.CTX_NEXT:
            self.ctx_action = ControlEvent.CTX_NEXT
            self.ctx_timer.start(self.CTX_TIMER_DELAY)
        elif event.name == ControlEvent.CTX_LAST:
            self.ctx_action = ControlEvent.CTX_LAST
            self.ctx_timer.start(self.CTX_TIMER_DELAY)
        elif event.name == ControlEvent.CTX_INPUT_FOCUS:
            self.window.controller.chat.common.focus_input()
            self.handle_result(event, True)
        elif event.name == ControlEvent.CTX_INPUT_CLEAR:
            self.window.controller.chat.input.clear_input()
            self.handle_result(event, True)
        elif event.name == ControlEvent.CTX_STOP:
            self.window.controller.chat.common.stop()
        elif event.name == ControlEvent.CTX_ATTACHMENTS_CLEAR:
            self.window.controller.attachment.clear(force=True)
        elif event.name == ControlEvent.CTX_CURRENT:
            status = self.window.core.access.helpers.get_current_ctx()
            if status != "":
                self.window.controller.audio.play_event(
                    status,
                    event,
                )
        elif event.name == ControlEvent.CTX_READ_LAST:
            text = self.window.core.access.helpers.get_last_ctx_item()
            if text != "":
                self.window.controller.audio.play_event(
                    text,
                    event,
                )
        elif event.name == ControlEvent.CTX_READ_ALL:
            text = self.window.core.access.helpers.get_all_ctx_items()
            if text != "":
                self.window.controller.audio.play_event(
                    text,
                    event,
                )
        elif event.name == ControlEvent.CTX_RENAME:
            if event.data is not None and "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.ctx.update_name_current(msg)
                    msg = trans("event.audio.ctx.rename").format(ctx=msg)
                    self.window.controller.audio.play_event(
                        msg,
                        event,
                    )
        elif event.name == ControlEvent.CTX_SEARCH_STRING:
            if event.data is not None and "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.ctx.append_search_string(msg)
                    num = self.window.core.ctx.count_found_meta()
                    msg = trans("event.audio.ctx.search.string").format(num=num)
                    self.window.controller.audio.play_event(
                        msg,
                        event,
                    )
        elif event.name == ControlEvent.CTX_SEARCH_CLEAR:
                self.window.controller.ctx.search_string_clear()
                self.handle_result(event, True)

        # calendar
        elif event.name == ControlEvent.CALENDAR_ADD:
            if event.data is not None and "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.calendar.note.append_text(msg)
                    self.handle_result(event, True)
        elif event.name == ControlEvent.CALENDAR_CLEAR:
            if force:
                self.window.controller.calendar.note.clear_note()
                self.handle_result(event, True)
            else:
                self.last_confirm = event
                self.window.controller.audio.play_event(
                    trans("event.audio.confirm"),
                    event,
                )
        elif event.name == ControlEvent.CALENDAR_READ:
            text = self.window.controller.calendar.note.get_note_text()
            self.window.controller.audio.play_event(
                text,
                event,
            )

        # mode change
        elif event.name == ControlEvent.MODE_CHAT:
            self.mode_action = ControlEvent.MODE_CHAT
            self.mode_timer.start(self.MODE_TIMER_DELAY)
        elif event.name == ControlEvent.MODE_LLAMA_INDEX:
            self.mode_action = ControlEvent.MODE_LLAMA_INDEX
            self.mode_timer.start(self.MODE_TIMER_DELAY)
        elif event.name == ControlEvent.MODE_NEXT:
            self.mode_action = ControlEvent.MODE_NEXT
            self.mode_timer.start(self.MODE_TIMER_DELAY)
        elif event.name == ControlEvent.MODE_PREV:
            self.mode_action = ControlEvent.MODE_PREV
            self.mode_timer.start(self.MODE_TIMER_DELAY)

        # model change
        elif event.name == ControlEvent.MODEL_NEXT:
            self.window.controller.model.next()
        elif event.name == ControlEvent.MODEL_PREV:
            self.window.controller.model.prev()

        # preset change
        elif event.name == ControlEvent.PRESET_NEXT:
            self.window.controller.presets.next()
        elif event.name == ControlEvent.PRESET_PREV:
            self.window.controller.presets.prev()

        # tab change
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
            if event.data is not None and "params" in event.data and event.data["params"] != "":
                try:
                    # regex extract number
                    num = re.findall(r'\d+', event.data["params"])
                    if len(num) > 0:
                        tmp_idx = int(num[0])
                except Exception as e:
                    print(e)
            self.window.controller.notepad.switch_to_tab(tmp_idx)
            self.handle_result(event, True)

        # voice control
        elif event.name == ControlEvent.VOICE_COMMAND_START:
            if not self.window.core.config.get("access.voice_control"):
                self.window.core.config.set("access.voice_control", True)
                self.window.controller.access.voice.update()
            self.window.controller.access.voice.start_recording()
        elif event.name == ControlEvent.VOICE_COMMAND_STOP:
            self.window.controller.access.voice.stop_recording()
        elif event.name == ControlEvent.VOICE_COMMAND_TOGGLE:
            if not self.window.core.config.get("access.voice_control"):
                self.window.core.config.set("access.voice_control", True)
                self.window.controller.access.voice.update()
            self.window.controller.access.voice.toggle_recording()

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

        # text input
        elif event.name == ControlEvent.INPUT_SEND:
            if event.data is not None and "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.chat.common.clear_input()
                    self.window.controller.chat.common.append_to_input(msg)
                self.window.controller.chat.input.send_input()
        elif event.name == ControlEvent.INPUT_APPEND:
            if event.data is not None and "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    self.window.controller.chat.common.append_to_input(msg)
                    self.handle_result(event, True)

        # notepad
        elif event.name == ControlEvent.NOTE_ADD:
            if event.data is not None and "params" in event.data:
                msg = event.data["params"]
                if msg != "":
                    if self.window.controller.notepad.is_active():
                        idx = self.window.controller.notepad.get_current_active()
                        self.window.controller.notepad.append_text(msg, idx)
                    else:
                        self.window.controller.notepad.append_text(msg, 1)
                    self.handle_result(event, True)
        elif event.name == ControlEvent.NOTEPAD_CLEAR:
            if force:
                if event.data is not None and "params" in event.data and event.data["params"] != "":
                    idx = 1
                    try:
                        # regex extract number
                        num = re.findall(r'\d+', event.data["params"])
                        if len(num) > 0:
                            idx = int(num[0])
                    except:
                        pass
                    if self.window.controller.notepad.clear(idx):
                        self.handle_result(event, True)
                else:
                    idx = self.window.controller.notepad.get_current_active()
                    if idx is not None and self.window.controller.notepad.clear(idx):
                        self.handle_result(event, True)
            else:
                self.last_confirm = event
                self.window.controller.audio.play_event(
                    trans("event.audio.confirm"),
                    event,
                )
        elif event.name == ControlEvent.NOTEPAD_READ:
            if event.data is not None and "params" in event.data and event.data["params"] != "":
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
            self.window.controller.audio.play_event(
                text,
                event,
            )

        # cmd list (help)
        elif event.name == ControlEvent.CMD_LIST:
            text = self.window.core.access.voice.get_commands_string(values=True)
            self.window.controller.audio.play_event(
                text,
                event,
            )

    def handle_result(self, event, result: bool = True):
        """
        Play result

        :param event: event object
        :param result: result
        """
        if not self.window.core.config.get("access.audio.event.speech"):
            return
        if self.window.core.access.voice.is_muted(event.name):
            return
        self.window.controller.audio.play_event(
            trans("event.audio." + event.name),
            event,
        )
