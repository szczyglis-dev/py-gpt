#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

from pygpt_net.core.events import RealtimeEvent

def build_rt_input_delta_event(
        rate: int,
        channels: int,
        data: bytes,
        final: bool
) -> RealtimeEvent:
    """
    Build RT_INPUT_AUDIO_DELTA event with a provider-agnostic payload.

    :param rate: Sample rate (e.g., 16000)
    :param channels: Number of channels (1 for mono, 2 for stereo)
    :param data: Audio data bytes
    :param final: Whether this is the final chunk
    :return: RealtimeEvent instance
    """
    return RealtimeEvent(
        RealtimeEvent.RT_INPUT_AUDIO_DELTA,
        {
            "payload": {
                "data": data or b"",
                "mime": "audio/pcm",
                "rate": int(rate),
                "channels": int(channels),
                "final": bool(final),
            }
        }
    )

def build_output_volume_event(value: int) -> RealtimeEvent:
    """
    Build RT_OUTPUT_AUDIO_VOLUME_CHANGED event.

    :param value: Volume level (0-100)
    :return: RealtimeEvent instance
    """
    return RealtimeEvent(
        RealtimeEvent.RT_OUTPUT_AUDIO_VOLUME_CHANGED,
        {"volume": int(value)}
    )