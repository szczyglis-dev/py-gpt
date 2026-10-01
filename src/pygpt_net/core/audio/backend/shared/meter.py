#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 14:40:00                  #
# ================================================== #

import math



class InputLevelMeter:
    """Convert microphone energy in the speech band to an immediate 0-100 level."""

    # Keep the meter focused on the frequency range carrying most speech
    # intelligibility. This naturally suppresses low-frequency rumble/hum and
    # high-frequency hiss without calibration, adaptive noise floors or gates.
    SPEECH_LOW_HZ = 250.0
    SPEECH_HIGH_HZ = 4000.0

    # Map speech-band RMS directly to the visible range. There is deliberately
    # no attack/release smoothing: every update represents the current chunk.
    FLOOR_DBFS = -42.0
    CEILING_DBFS = -18.0

    def reset(self):
        """Compatibility no-op; the meter intentionally keeps no state."""
        return None

    def update(
            self,
            samples,
            sample_rate: float,
            full_scale: float = 1.0,
            channels: int = 1,
    ) -> int:
        """
        Return an immediate 0-100 level based only on speech-band energy.

        The input chunk is normalized to full scale, transformed to the
        frequency domain, restricted to ``SPEECH_LOW_HZ..SPEECH_HIGH_HZ`` and
        converted back to RMS. No calibration, noise estimation, gating,
        hysteresis, attack or release is applied.
        """
        try:
            sample_rate = float(sample_rate)
            full_scale = abs(float(full_scale))
            channels = max(1, int(channels))
        except (TypeError, ValueError):
            return 0

        if (not math.isfinite(sample_rate) or sample_rate <= 0.0
                or not math.isfinite(full_scale) or full_scale <= 0.0):
            return 0

        try:
            import numpy as np
            audio = np.asarray(samples, dtype=np.float64).reshape(-1)
        except (TypeError, ValueError):
            return 0

        if audio.size < 8:
            return 0

        # Preserve channel separation so opposite-polarity stereo channels do
        # not cancel each other before metering.
        usable = audio.size - (audio.size % channels)
        if usable < channels * 8:
            return 0
        audio = audio[:usable].reshape(-1, channels) / full_scale
        audio -= np.mean(audio, axis=0, keepdims=True)

        frame_count = audio.shape[0]
        nyquist = sample_rate * 0.5
        high_hz = min(self.SPEECH_HIGH_HZ, nyquist)
        if high_hz <= self.SPEECH_LOW_HZ:
            return 0

        # A Hann window limits leakage from strong frequencies just outside the
        # speech band. Compensate its RMS loss so in-band levels stay natural.
        window = np.hanning(frame_count)
        window_rms = float(np.sqrt(np.mean(window * window)))
        if window_rms <= 0.0:
            return 0

        spectrum = np.fft.rfft(audio * window[:, None], axis=0)
        freqs = np.fft.rfftfreq(frame_count, d=1.0 / sample_rate)
        mask = (freqs >= self.SPEECH_LOW_HZ) & (freqs <= high_hz)
        if not np.any(mask):
            return 0

        spectrum[~mask, :] = 0.0
        filtered = np.fft.irfft(spectrum, n=frame_count, axis=0)
        rms = float(np.sqrt(np.mean(filtered * filtered))) / window_rms

        if not math.isfinite(rms) or rms <= 0.0:
            return 0

        dbfs = 20.0 * math.log10(max(rms, 1e-12))
        if dbfs <= self.FLOOR_DBFS:
            return 0
        if dbfs >= self.CEILING_DBFS:
            return 100

        value = (dbfs - self.FLOOR_DBFS) / (self.CEILING_DBFS - self.FLOOR_DBFS)
        return int(round(value * 100.0))
