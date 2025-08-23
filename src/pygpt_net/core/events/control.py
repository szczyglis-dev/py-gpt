#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 21:00:00                  #
# ================================================== #

from typing import Optional

from .base import BaseEvent


class ControlEvent(BaseEvent):
    """Events used for app control"""
    APP_EXIT = "app.exit"
    APP_STATUS = "app.status"
    AUDIO_INPUT_DISABLE = "audio.input.disable"
    AUDIO_INPUT_ENABLE = "audio.input.enable"
    AUDIO_OUTPUT_DISABLE = "audio.output.disable"
    AUDIO_OUTPUT_ENABLE = "audio.output.enable"
    CALENDAR_ADD = "calendar.add"
    CALENDAR_CLEAR = "calendar.clear"
    CALENDAR_READ = "calendar.read"
    CAMERA_CAPTURE = "camera.capture"
    CAMERA_DISABLE = "camera.disable"
    CAMERA_ENABLE = "camera.enable"
    CMD_CONFIRM = "cmd.confirm"
    CMD_LIST = "cmd.list"
    CTX_ATTACHMENTS_CLEAR = "ctx.attachments.clear"
    CTX_CURRENT = "ctx.current"
    CTX_INPUT_CLEAR = "ctx.input.clear"
    CTX_INPUT_FOCUS = "ctx.input.focus"
    CTX_INPUT_SEND = "ctx.input.send"
    CTX_LAST = "ctx.last"
    CTX_NEW = "ctx.new"
    CTX_NEXT = "ctx.next"
    CTX_PREV = "ctx.prev"
    CTX_READ_ALL = "ctx.read.all"
    CTX_READ_LAST = "ctx.read.last"
    CTX_RENAME = "ctx.rename"
    CTX_SEARCH_CLEAR = "ctx.search.clear"
    CTX_SEARCH_STRING = "ctx.search.string"
    CTX_STOP = "ctx.stop"
    INPUT_APPEND = "input.append"
    INPUT_SEND = "input.send"
    MODE_CHAT = "mode.chat"
    MODE_LLAMA_INDEX = "mode.llama_index"
    MODE_NEXT = "mode.next"
    MODE_PREV = "mode.prev"
    MODE_RESEARCH = "mode.research"
    MODEL_NEXT = "model.next"
    MODEL_PREV = "model.prev"
    NOTE_ADD = "note.add"
    NOTEPAD_CLEAR = "notepad.clear"
    NOTEPAD_READ = "notepad.read"
    PRESET_NEXT = "preset.next"
    PRESET_PREV = "preset.prev"
    TAB_CALENDAR = "tab.calendar"
    TAB_CHAT = "tab.chat"
    TAB_DRAW = "tab.draw"
    TAB_FILES = "tab.files"
    TAB_NEXT = "tab.next"
    TAB_NOTEPAD = "tab.notepad"
    TAB_PREV = "tab.prev"
    VOICE_COMMAND_START = "voice_cmd.start"
    VOICE_COMMAND_STOP = "voice_cmd.stop"
    VOICE_COMMAND_TOGGLE = "voice_cmd.toggle"
    VOICE_CONTROL_UNRECOGNIZED = "unrecognized"
    VOICE_MESSAGE_START = "voice_msg.start"
    VOICE_MESSAGE_STOP = "voice_msg.stop"
    VOICE_MESSAGE_TOGGLE = "voice_msg.toggle"

    def __init__(
            self,
            name: Optional[str] = None,
            data: Optional[dict] = None,
    ):
        """
        Event object class

        :param name: event name
        :param data: event data
        """
        super(ControlEvent, self).__init__(name, data)
        self.id = "ControlEvent"