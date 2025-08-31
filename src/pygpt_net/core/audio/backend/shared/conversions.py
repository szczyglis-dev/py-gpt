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

import numpy as np
import audioop

def qaudio_dtype(sample_format):
    """
    Map QAudioFormat.SampleFormat to numpy dtype.

    Raises ValueError if the format is unsupported.

    :param sample_format: QAudioFormat.SampleFormat
    :return: numpy dtype
    """
    try:
        from PySide6.QtMultimedia import QAudioFormat
    except Exception:
        raise

    if sample_format == QAudioFormat.SampleFormat.UInt8:
        return np.uint8
    elif sample_format == QAudioFormat.SampleFormat.Int16:
        return np.int16
    elif sample_format == QAudioFormat.SampleFormat.Int32:
        return np.int32
    elif sample_format == QAudioFormat.SampleFormat.Float:
        return np.float32
    raise ValueError("Unsupported sample format")

def qaudio_norm_factor(sample_format):
    """
    Normalization factor for QAudioFormat.SampleFormat.

    Raises ValueError if the format is unsupported.

    :param sample_format: QAudioFormat.SampleFormat
    :return: normalization factor (float)
    """
    try:
        from PySide6.QtMultimedia import QAudioFormat
    except Exception:
        raise

    if sample_format == QAudioFormat.SampleFormat.UInt8:
        return 255.0
    elif sample_format == QAudioFormat.SampleFormat.Int16:
        return 32768.0
    elif sample_format == QAudioFormat.SampleFormat.Int32:
        return float(2 ** 31)
    elif sample_format == QAudioFormat.SampleFormat.Float:
        return 1.0
    raise ValueError("Unsupported sample format")

def qaudio_to_s16le(raw: bytes, sample_format) -> bytes:
    """
    Convert arbitrary QAudioFormat sample format to PCM16 little-endian.

    :param raw: input byte buffer
    :param sample_format: QAudioFormat.SampleFormat
    :return: converted byte buffer in PCM16 little-endian
    """
    if not raw:
        return b""
    try:
        from PySide6.QtMultimedia import QAudioFormat
    except Exception:
        return raw

    if sample_format == QAudioFormat.SampleFormat.Int16:
        return raw
    elif sample_format == QAudioFormat.SampleFormat.UInt8:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.int16)
        arr = (arr - 128) << 8
        return arr.tobytes()
    elif sample_format == QAudioFormat.SampleFormat.Int32:
        arr = np.frombuffer(raw, dtype=np.int32)
        arr = (arr >> 16).astype(np.int16)
        return arr.tobytes()
    elif sample_format == QAudioFormat.SampleFormat.Float:
        arr = np.frombuffer(raw, dtype=np.float32)
        arr = np.clip(arr, -1.0, 1.0)
        arr = (arr * 32767.0).astype(np.int16)
        return arr.tobytes()
    return raw

def pyaudio_to_s16le(raw: bytes, fmt, pa_instance=None) -> bytes:
    """
    Convert PyAudio input buffer to PCM16 little-endian without changing
    sample rate or channel count.

    :param raw: input byte buffer
    :param fmt: PyAudio format (e.g., pyaudio.paInt16)
    :param pa_instance: Optional PyAudio instance for sample size queries
    :return: converted byte buffer in PCM16 little-endian
    """
    if not raw:
        return b""
    try:
        import pyaudio
    except Exception:
        return raw

    try:
        if fmt == pyaudio.paInt16:
            return raw
        elif fmt == pyaudio.paUInt8:
            arr = np.frombuffer(raw, dtype=np.uint8).astype(np.int16)
            arr = (arr - 128) << 8
            return arr.tobytes()
        elif fmt == pyaudio.paInt8:
            arr = np.frombuffer(raw, dtype=np.int8).astype(np.int16)
            arr = (arr.astype(np.int16) << 8)
            return arr.tobytes()
        elif fmt == pyaudio.paFloat32:
            arr = np.frombuffer(raw, dtype=np.float32)
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767.0).astype(np.int16)
            return arr.tobytes()
        else:
            try:
                sw = pa_instance.get_sample_size(fmt) if pa_instance is not None else 2
                return audioop.lin2lin(raw, sw, 2)
            except Exception:
                return raw
    except Exception:
        return raw

def f32_to_s16le(raw: bytes) -> bytes:
    """
    Convert float32 little-endian PCM to int16 little-endian PCM.

    :param raw: input byte buffer in float32
    :return: converted byte buffer in int16
    """
    if not raw:
        return b""
    try:
        arr = np.frombuffer(raw, dtype=np.float32)
        arr = np.clip(arr, -1.0, 1.0)
        s16 = (arr * 32767.0).astype(np.int16)
        return s16.tobytes()
    except Exception:
        return b""

def convert_s16_pcm(
    data: bytes,
    in_rate: int,
    in_channels: int,
    out_rate: int,
    out_channels: int,
    out_width: int = 2,
    out_format: str = "s16"  # "s16" | "u8" | "f32"
) -> bytes:
    """
    Minimal PCM converter to target format:
    - assumes input is S16LE,
    - converts channels (mono<->stereo) and sample rate,
    - converts width if needed,
    - applies bias for u8 or float conversion if requested.

    :param data: input byte buffer in S16LE
    :param in_rate: input sample rate
    :param in_channels: input channel count
    :param out_rate: output sample rate
    :param out_channels: output channel count
    :param out_width: output sample width in bytes (1, 2, or 4)
    :param out_format: output format ("s16", "u8", or "f32")
    :return: converted byte buffer
    """
    if not data:
        return b""
    try:
        src = data

        # channels
        if in_channels != out_channels:
            if in_channels == 2 and out_channels == 1:
                src = audioop.tomono(src, 2, 0.5, 0.5)
            elif in_channels == 1 and out_channels == 2:
                src = audioop.tostereo(src, 2, 1.0, 1.0)
            else:
                mid = audioop.tomono(src, 2, 0.5, 0.5) if in_channels > 1 else src
                src = audioop.tostereo(mid, 2, 1.0, 1.0) if out_channels == 2 else mid

        # sample rate
        if in_rate != out_rate:
            src, _ = audioop.ratecv(src, 2, out_channels, in_rate, out_rate, None)

        # sample width (Int16 -> other widths if needed)
        if out_width != 2:
            src = audioop.lin2lin(src, 2, out_width)

        # sample format nuances
        if out_format == "u8" and out_width == 1:
            src = audioop.bias(src, 1, 128)  # center at 0x80
        elif out_format == "f32" and out_width == 4:
            arr = np.frombuffer(src, dtype=np.int16).astype(np.float32) / 32768.0
            src = arr.tobytes()

        return src
    except Exception:
        return data