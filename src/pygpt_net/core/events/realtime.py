#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

from typing import Optional

from .base import BaseEvent


class RealtimeEvent(BaseEvent):
    """
    Realtime events

    - AUDIO_OUTPUT_CHUNK - audio output chunk (with payload)
    - AUDIO_OUTPUT_READY - audio output is ready (STREAM_BEGIN)
    - AUDIO_OUTPUT_TEXT_CHUNK - text chunk (delta)
    - AUDIO_OUTPUT_END - audio output ended (STREAM_END)
    - AUDIO_OUTPUT_ERROR - audio output error (STREAM_ERROR)
    - AUDIO_OUTPUT_VOLUME_CHANGED - audio output volume changed (volume level)
    """

    # core, events sent from kernel
    AUDIO_OUTPUT_CHUNK = "realtime.audio.output.chunk"
    AUDIO_OUTPUT_READY = "realtime.audio.output.ready"
    AUDIO_OUTPUT_TEXT_CHUNK = "realtime.audio.output.text.chunk"
    AUDIO_OUTPUT_END = "realtime.audio.output.end"
    AUDIO_OUTPUT_ERROR = "realtime.audio.output.error"
    AUDIO_OUTPUT_VOLUME_CHANGED = "realtime.audio.output.volume.changed"

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
        super(RealtimeEvent, self).__init__(name, data)
        self.id = "RealtimeEvent"
