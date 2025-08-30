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

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class RealtimeOptions:
    """
    Options for starting a realtime session.

    :param provider: Provider name ("google" or "openai")
    :param model: Model name
    :param system_prompt: System prompt text
    :param prompt: User prompt text
    :param voice: Voice name for TTS
    :param audio_data: Optional input audio data (bytes)
    :param audio_format: Format of the input audio (e.g., "pcm16", "wav")
    :param audio_rate: Sample rate of the input audio (e.g., 16000)
    :param vad: Voice Activity Detection mode (e.g., "server_vad" or None for manual)
    :param extra: Free-form dictionary for extra parameters
    :param rt_signals: Real-time signals for event handling
    """
    provider: str = "google"  # "google" | "openai"
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    prompt: Optional[str] = None
    voice: Optional[str] = None

    # Optional input audio
    audio_data: Optional[bytes] = None
    audio_format: Optional[str] = None  # e.g., "pcm16", "wav"
    audio_rate: Optional[int] = None    # e.g., 16000

    # Provider-specific VAD flag (use None for manual mode)
    vad: Optional[str] = None           # e.g., "server_vad"

    # Free-form extra
    extra: dict = field(default_factory=dict)

    # Real-time signals
    rt_signals: field() = None  # RT signals