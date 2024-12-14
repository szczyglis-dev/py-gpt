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

from typing import Optional

from .base import BaseEvent

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
    MODE_SELECTED = "mode.selected"
    MODEL_SELECTED = "model.selected"
    PRESET_SELECTED = "preset.selected"
    TAB_SELECTED = "tab.switch"
    VOICE_CONTROL_TOGGLE = "voice.control.toggle"
    VOICE_CONTROL_STARTED = "voice.control.started"
    VOICE_CONTROL_STOPPED = "voice.control.stopped"
    VOICE_CONTROL_SENT = "voice.control.sent"
    VOICE_CONTROL_UNRECOGNIZED = "voice.control.unrecognized"

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
        super(AppEvent, self).__init__(name, data)
        self.id = "AppEvent"
