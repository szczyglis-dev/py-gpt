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

import math


class InputLevelMeter:
    """Convert normalized audio RMS to a responsive 0-100 dBFS meter."""

    # An RMS meter mapped all the way to 0 dBFS rarely reaches the end during
    # normal speech. -6 dBFS is a practical upper reference for an input/VU
    # indicator, while values below -55 dBFS are treated as silence/noise.
    FLOOR_DBFS = -55.0
    CEILING_DBFS = -6.0

    # Faster attack and slower release make speech responsive without making
    # the bar flicker between consecutive audio chunks.
    ATTACK = 0.72
    RELEASE = 0.20

    def __init__(self):
        self._value = 0.0

    def reset(self):
        """Reset the smoothed meter value."""
        self._value = 0.0

    def update(self, rms: float, full_scale: float = 1.0) -> int:
        """
        Convert RMS amplitude to a smoothed 0-100 dBFS display value.

        ``full_scale`` is the maximum representable amplitude of the current
        sample format. This makes the result relative to the actual audio
        format instead of treating raw RMS values as linear percentages.
        """
        try:
            rms = abs(float(rms))
            full_scale = abs(float(full_scale))
        except (TypeError, ValueError):
            return int(round(self._value))

        if (not math.isfinite(rms) or not math.isfinite(full_scale)
                or full_scale <= 0.0 or rms <= 0.0):
            target = 0.0
        else:
            normalized = min(rms / full_scale, 1.0)
            dbfs = 20.0 * math.log10(max(normalized, 1e-12))

            if dbfs <= self.FLOOR_DBFS:
                target = 0.0
            else:
                span = self.CEILING_DBFS - self.FLOOR_DBFS
                target = ((dbfs - self.FLOOR_DBFS) / span) * 100.0
                target = min(max(target, 0.0), 100.0)

        factor = self.ATTACK if target > self._value else self.RELEASE
        self._value += (target - self._value) * factor

        # Let the bar fully settle at zero instead of leaving a tiny pixel.
        if target == 0.0 and self._value < 0.5:
            self._value = 0.0

        return int(round(min(max(self._value, 0.0), 100.0)))
