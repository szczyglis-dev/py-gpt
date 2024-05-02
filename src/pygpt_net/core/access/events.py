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

from pygpt_net.core.dispatcher import BaseEvent


class ControlEvent(BaseEvent):
    """Events used for app control"""
    APP_STATUS = "app.status"
    APP_EXIT = "app.exit"
    AUDIO_OUTPUT_ENABLE = "audio.output.enable"
    AUDIO_OUTPUT_DISABLE = "audio.output.disable"
    AUDIO_INPUT_ENABLE = "audio.input.enable"
    AUDIO_INPUT_DISABLE = "audio.input.disable"
    CAMERA_ENABLE = "camera.enable"
    CAMERA_DISABLE = "camera.disable"
    CAMERA_CAPTURE = "camera.capture"
    CTX_NEW = "ctx.new"
    CTX_PREV = "ctx.prev"
    CTX_NEXT = "ctx.next"
    CTX_LAST = "ctx.last"
    CTX_INPUT_FOCUS = "ctx.input.focus"
    CTX_INPUT_SEND = "ctx.input.send"
    CTX_INPUT_CLEAR = "ctx.input.clear"
    CTX_STOP = "ctx.stop"
    CTX_ATTACHMENTS_CLEAR = "ctx.attachments.clear"
    CTX_CURRENT = "ctx.current"
    CTX_READ_LAST = "ctx.read.last"
    CTX_READ_ALL = "ctx.read.all"
    INPUT_SEND = "input.send"
    INPUT_APPEND = "input.append"
    MODE_CHAT = "mode.chat"
    MODE_LLAMA_INDEX = "mode.llama_index"
    NOTE_ADD = "note.add"
    NOTEPAD_READ = "notepad.read"
    TAB_CHAT = "tab.chat"
    TAB_CALENDAR = "tab.calendar"
    TAB_DRAW = "tab.draw"
    TAB_FILES = "tab.files"
    TAB_NOTEPAD = "tab.notepad"
    TAB_NEXT = "tab.next"
    TAB_PREV = "tab.prev"
    VOICE_MESSAGE_START = "voice_msg.start"
    VOICE_MESSAGE_STOP = "voice_msg.stop"
    VOICE_MESSAGE_TOGGLE = "voice_msg.toggle"
    VOICE_COMMAND_START = "voice_cmd.start"
    VOICE_COMMAND_STOP = "voice_cmd.stop"
    VOICE_COMMAND_TOGGLE = "voice_cmd.toggle"


class AppEvent(BaseEvent):
    """Events dispatched by application"""
    APP_STARTED = "app.started"
    CTX_CREATED = "ctx.created"
    CTX_END = "ctx.end"
    CTX_SELECTED = "ctx.selected"
    CTX_ATTACHMENTS_CLEAR = "ctx.attachments.clear"
    CAMERA_ENABLED = "camera.enabled"
    CAMERA_DISABLED = "camera.disabled"
    CAMERA_CAPTURED = "camera.captured"
    INPUT_ERROR = "input.error"
    INPUT_SENT = "input.sent"
    INPUT_CALL = "input.call"
    INPUT_STOPPED = "input.stopped"
    INPUT_VOICE_LISTEN_STARTED = "input.voice.listen.started"
    INPUT_VOICE_LISTEN_STOPPED = "input.voice.listen.stopped"
    VOICE_CONTROL_TOGGLE = "voice.control.toggle"
    VOICE_CONTROL_STARTED = "voice.control.started"
    VOICE_CONTROL_STOPPED = "voice.control.stopped"
    VOICE_CONTROL_SENT = "voice.control.sent"
    VOICE_CONTROL_UNRECOGNIZED = "voice.control.unrecognized"
