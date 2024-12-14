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

from typing import List, Dict

from pygpt_net.core.events import ControlEvent, AppEvent


class Actions:
    def __init__(self, window=None):
        """
        Actions core

        :param window: Window instance
        """
        self.window = window

    def get_access_choices(self) -> List[Dict[str, str]]:
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

    def get_speech_synthesis_choices(self) -> List[Dict[str, str]]:
        """
        Get app access events choices

        :return: choices
        """
        events_list_control = [
            ControlEvent.CALENDAR_ADD,
            ControlEvent.CALENDAR_CLEAR,
            ControlEvent.CTX_RENAME,
            ControlEvent.CTX_SEARCH_STRING,
            ControlEvent.CTX_SEARCH_CLEAR,
            ControlEvent.INPUT_APPEND,
            ControlEvent.NOTE_ADD,
            ControlEvent.NOTEPAD_CLEAR,
        ]
        events_list_app = [
            AppEvent.APP_STARTED,
            AppEvent.CTX_CREATED,
            AppEvent.CTX_END,
            AppEvent.CTX_SELECTED,
            AppEvent.CTX_ATTACHMENTS_CLEAR,
            AppEvent.CAMERA_ENABLED,
            AppEvent.CAMERA_DISABLED,
            AppEvent.CAMERA_CAPTURED,
            AppEvent.INPUT_ERROR,
            AppEvent.INPUT_SENT,
            AppEvent.INPUT_STOPPED,
            AppEvent.MODE_SELECTED,
            AppEvent.MODEL_SELECTED,
            AppEvent.PRESET_SELECTED,
            AppEvent.TAB_SELECTED,
        ]
        # build choices
        choices = []
        for event in events_list_control:
            choices.append({event: f"event.audio.{event}"})
        for event in events_list_app:
            choices.append({event: f"event.audio.{event}"})
        return choices

    def get_voice_control_choices(self) -> List[Dict[str, str]]:
        """
        Get voice control choices

        :return: choices
        """
        actions = self.window.core.access.voice.get_commands().items()
        # build choices
        choices = []
        for k, v in actions:
            choices.append({k: v})
        return choices