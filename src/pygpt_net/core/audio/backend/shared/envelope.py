#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 04:00:00                  #
# ================================================== #

import numpy as np
from pydub import AudioSegment

def compute_envelope_from_file(audio_file: str, chunk_ms: int = 100) -> list:
    """
    Calculate the volume envelope of an audio file (0-100 per chunk).

    :param audio_file: Path to the audio file
    :param chunk_ms: Chunk size in milliseconds
    :return: List of volume levels (0-100) per chunk
    """
    audio = AudioSegment.from_file(audio_file)
    max_amplitude = 32767.0
    envelope = []

    for ms in range(0, len(audio), chunk_ms):
        chunk = audio[ms:ms + chunk_ms]
        rms = float(chunk.rms) if chunk.rms else 0.0
        if rms > 0.0:
            db = 20.0 * np.log10(max(1e-12, rms / max_amplitude))
        else:
            db = -60.0
        db = max(-60.0, min(0.0, db))
        volume = ((db + 60.0) / 60.0) * 100.0
        envelope.append(volume)

    return envelope