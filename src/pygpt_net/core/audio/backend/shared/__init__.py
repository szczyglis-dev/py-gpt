#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 17:32:00                  #
# ================================================== #

# Shared helpers for audio backends

from .rt import (
    build_rt_input_delta_event,
    build_output_volume_event,
)
from .conversions import (
    qaudio_dtype,
    qaudio_norm_factor,
    qaudio_to_s16le,
    pyaudio_to_s16le,
    f32_to_s16le,
    convert_s16_pcm,
)
from .envelope import compute_envelope_from_file
from .meter import InputLevelMeter

__all__ = [
    "build_rt_input_delta_event",
    "build_output_volume_event",
    "qaudio_dtype",
    "qaudio_norm_factor",
    "qaudio_to_s16le",
    "pyaudio_to_s16le",
    "f32_to_s16le",
    "convert_s16_pcm",
    "compute_envelope_from_file",
    "InputLevelMeter",
]
