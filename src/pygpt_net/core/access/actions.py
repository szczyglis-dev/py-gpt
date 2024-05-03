#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.03 12:00:00                  #
# ================================================== #

from .events import ControlEvent


class Actions:
    def __init__(self, window=None):
        """
        Actions core

        :param window: Window instance
        """
        self.window = window

    def get_access_choices(self) -> list:
        """
        Get app access events choices

        :return: choices
        """
        events_list = [
            ControlEvent.APP_STATUS,
            ControlEvent.APP_EXIT,
            ControlEvent.AUDIO_OUTPUT_ENABLE,
            ControlEvent.AUDIO_OUTPUT_DISABLE,
            ControlEvent.AUDIO_INPUT_ENABLE,
            ControlEvent.AUDIO_INPUT_DISABLE,
            ControlEvent.CAMERA_ENABLE,
            ControlEvent.CAMERA_DISABLE,
            ControlEvent.CAMERA_CAPTURE,
            ControlEvent.CTX_NEW,
            ControlEvent.CTX_PREV,
            ControlEvent.CTX_NEXT,
            ControlEvent.CTX_LAST,
            ControlEvent.CTX_INPUT_FOCUS,
            ControlEvent.CTX_INPUT_SEND,
            ControlEvent.CTX_INPUT_CLEAR,
            ControlEvent.CTX_STOP,
            ControlEvent.CTX_ATTACHMENTS_CLEAR,
            ControlEvent.MODE_CHAT,
            ControlEvent.MODE_LLAMA_INDEX,
            ControlEvent.MODE_NEXT,
            ControlEvent.MODE_PREV,
            ControlEvent.MODEL_NEXT,
            ControlEvent.MODEL_PREV,
            ControlEvent.PRESET_NEXT,
            ControlEvent.PRESET_PREV,
            ControlEvent.TAB_CHAT,
            ControlEvent.TAB_CALENDAR,
            ControlEvent.TAB_DRAW,
            ControlEvent.TAB_FILES,
            ControlEvent.TAB_NOTEPAD,
            ControlEvent.TAB_NEXT,
            ControlEvent.TAB_PREV,
            ControlEvent.VOICE_MESSAGE_START,
            ControlEvent.VOICE_MESSAGE_STOP,
            ControlEvent.VOICE_MESSAGE_TOGGLE,
            ControlEvent.VOICE_COMMAND_START,
            ControlEvent.VOICE_COMMAND_STOP,
            ControlEvent.VOICE_COMMAND_TOGGLE,
        ]
        # build choices
        choices = []
        for event in events_list:
            choices.append({event: f"event.control.{event}"})
        return choices