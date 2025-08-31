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
    provider: str = "openai"  # "google" | "openai"
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

    vad_end_silence_ms: Optional[int] = 2000  # VAD end silence in ms
    vad_prefix_padding_ms: Optional[int] = 300  # VAD prefix padding in ms

    # Real-time signals
    rt_signals: field() = None  # RT signals

    # Tools and remote tools
    tools: Optional[list] = None
    remote_tools: Optional[list] = None

    # Auto-turn enable/disable
    auto_turn: Optional[bool] = False

    # Transcript enable/disable
    transcribe: Optional[bool] = True

    # Last session ID
    rt_session_id: Optional[str] = None

    # Extra parameters
    extra: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "prompt": self.prompt,
            "voice": self.voice,
            "audio_data (len)": len(self.audio_data) if self.audio_data else 0,
            "audio_format": self.audio_format,
            "audio_rate": self.audio_rate,
            "vad": self.vad,
            "vad_end_silence_ms": self.vad_end_silence_ms,
            "vad_prefix_padding_ms": self.vad_prefix_padding_ms,
            "tools": self.tools,
            "remote_tools": self.remote_tools,
            "auto_turn": self.auto_turn,
            "transcribe": self.transcribe,
            "rt_session_id": self.rt_session_id,
            "extra": self.extra,
        }