import sys
from types import SimpleNamespace

import numpy as np
import pytest

from pygpt_net.core.audio.backend.shared.conversions import (
    convert_s16_pcm,
    f32_to_s16le,
    pyaudio_to_s16le,
    qaudio_dtype,
    qaudio_norm_factor,
    qaudio_to_s16le,
)


class SampleFormat:
    UInt8 = object()
    Int16 = object()
    Int32 = object()
    Float = object()


def _fake_qt(monkeypatch):
    module = SimpleNamespace(QAudioFormat=SimpleNamespace(SampleFormat=SampleFormat))
    monkeypatch.setitem(sys.modules, "PySide6.QtMultimedia", module)


def test_qaudio_dtype_and_normalization(monkeypatch):
    _fake_qt(monkeypatch)
    assert qaudio_dtype(SampleFormat.UInt8) is np.uint8
    assert qaudio_dtype(SampleFormat.Int16) is np.int16
    assert qaudio_dtype(SampleFormat.Int32) is np.int32
    assert qaudio_dtype(SampleFormat.Float) is np.float32
    assert qaudio_norm_factor(SampleFormat.UInt8) == 255.0
    assert qaudio_norm_factor(SampleFormat.Int16) == 32768.0
    assert qaudio_norm_factor(SampleFormat.Int32) == float(2 ** 31)
    assert qaudio_norm_factor(SampleFormat.Float) == 1.0
    with pytest.raises(ValueError):
        qaudio_dtype(object())


def test_qaudio_to_s16le_converts_supported_formats(monkeypatch):
    _fake_qt(monkeypatch)
    assert qaudio_to_s16le(b"", SampleFormat.Int16) == b""
    raw16 = np.array([-32768, 32767], dtype=np.int16).tobytes()
    assert qaudio_to_s16le(raw16, SampleFormat.Int16) == raw16

    u8 = np.array([0, 128, 255], dtype=np.uint8).tobytes()
    converted = np.frombuffer(qaudio_to_s16le(u8, SampleFormat.UInt8), dtype=np.int16)
    assert converted.tolist() == [-32768, 0, 32512]

    f32 = np.array([-2.0, 0.5, 2.0], dtype=np.float32).tobytes()
    converted = np.frombuffer(qaudio_to_s16le(f32, SampleFormat.Float), dtype=np.int16)
    assert converted.tolist() == [-32767, 16383, 32767]


def test_pyaudio_to_s16le_handles_common_formats(monkeypatch):
    fake = SimpleNamespace(paInt16=1, paUInt8=2, paInt8=3, paFloat32=4)
    monkeypatch.setitem(sys.modules, "pyaudio", fake)

    raw16 = np.array([1, -1], dtype=np.int16).tobytes()
    assert pyaudio_to_s16le(raw16, fake.paInt16) == raw16
    converted = np.frombuffer(pyaudio_to_s16le(bytes([0, 128, 255]), fake.paUInt8), dtype=np.int16)
    assert converted.tolist() == [-32768, 0, 32512]


def test_f32_to_s16le_clips_and_empty_input():
    assert f32_to_s16le(b"") == b""
    raw = np.array([-2.0, 0.0, 2.0], dtype=np.float32).tobytes()
    assert np.frombuffer(f32_to_s16le(raw), dtype=np.int16).tolist() == [-32767, 0, 32767]


def test_convert_s16_pcm_handles_channels_and_empty_input():
    assert convert_s16_pcm(b"", 16000, 1, 16000, 1) == b""
    mono = np.array([1000, -1000], dtype=np.int16).tobytes()
    stereo = convert_s16_pcm(mono, 16000, 1, 16000, 2)
    values = np.frombuffer(stereo, dtype=np.int16)
    assert values.tolist() == [1000, 1000, -1000, -1000]
