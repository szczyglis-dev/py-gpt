import asyncio
import io
import math
import struct
import wave

import pytest

from pygpt_net.core.realtime.shared.audio import (
    coerce_to_pcm16_mono,
    dump_wav,
    float32_to_int16_bytes,
    iter_pcm_chunks,
    parse_wav_fmt,
    pcm16_stats,
    resample_pcm16_mono,
    to_pcm16_mono,
)
from pygpt_net.core.realtime.shared.loop import BackgroundLoop


def make_wav(samples, *, rate=8000, channels=1, width=2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(samples)
    return buf.getvalue()


def test_coerce_raw_and_empty_inputs():
    assert coerce_to_pcm16_mono(b"", None, None) == (24000, 1, b"")
    assert coerce_to_pcm16_mono(b"\x01\x00", "pcm16", 16000) == (16000, 1, b"\x01\x00")


def test_coerce_wav_mixes_stereo_to_mono():
    stereo = struct.pack("<hhhh", 1000, -1000, 2000, 0)
    data = make_wav(stereo, rate=8000, channels=2)
    rate, channels, pcm = coerce_to_pcm16_mono(data, "wav", None)
    assert rate == 8000 and channels == 1
    values = struct.unpack("<hh", pcm)
    assert values == (0, 1000)


def test_coerce_invalid_wav_falls_back_to_raw_and_rate_hint():
    payload = b"not-a-wav"
    assert coerce_to_pcm16_mono(payload, "wav", 12345) == (12345, 1, payload)


def test_float32_to_int16_clips_and_scales():
    raw = struct.pack("<fffff", -2.0, -1.0, 0.0, 1.0, 2.0)
    result = struct.unpack("<hhhhh", float32_to_int16_bytes(raw))
    assert result == (-32768, -32767, 0, 32767, 32767)
    assert float32_to_int16_bytes(b"") == b""


def test_parse_wav_fmt_reads_pcm_metadata_and_rejects_invalid():
    data = make_wav(struct.pack("<hh", 1, 2), rate=22050, channels=1)
    info = parse_wav_fmt(data)
    assert info["format_tag"] == 1
    assert info["channels"] == 1
    assert info["sample_rate"] == 22050
    assert info["bits_per_sample"] == 16
    assert parse_wav_fmt(b"bad") is None


def test_to_pcm16_mono_raw_resamples_and_returns_target_rate():
    pcm = struct.pack("<" + "h" * 16, *range(16))
    out, rate = to_pcm16_mono(pcm, "raw", 8000, 16000)
    assert rate == 16000
    assert out
    assert len(out) > len(pcm)


def test_to_pcm16_mono_wav_and_invalid_input():
    mono = struct.pack("<hhh", 100, 200, 300)
    wav = make_wav(mono, rate=8000, channels=1)
    out, rate = to_pcm16_mono(wav, "wav", None, 8000)
    assert (out, rate) == (mono, 8000)
    assert to_pcm16_mono(b"not-wav", "wav", None, 16000) == (b"", 16000)


def test_resample_and_chunks_handle_identity_and_sizes():
    pcm = struct.pack("<" + "h" * 100, *range(100))
    assert resample_pcm16_mono(pcm, 8000, 8000) is pcm
    out = resample_pcm16_mono(pcm, 8000, 16000)
    assert len(out) > len(pcm)
    chunks = iter_pcm_chunks(pcm, 1000, ms=10)
    assert [len(x) for x in chunks[:-1]] == [20] * (len(chunks) - 1)
    assert b"".join(chunks) == pcm


def test_dump_wav_and_stats(tmp_path):
    pcm = struct.pack("<hhhh", 0, 1000, -1000, 2000)
    path = tmp_path / "nested" / "audio.wav"
    dump_wav(str(path), 16000, pcm)
    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        assert wf.readframes(wf.getnframes()) == pcm
    stats = pcm16_stats(pcm, 16000)
    assert stats["samples"] == 4
    assert stats["duration_s"] == pytest.approx(4 / 16000)
    assert stats["peak"] == 2000
    assert math.isfinite(stats["dbfs"])
    silence = pcm16_stats(b"\x00\x00" * 2, 16000)
    assert silence["dbfs"] == -999.0


def test_background_loop_run_sync_run_async_and_stop():
    loop = BackgroundLoop(name="test-loop")
    try:
        pending = asyncio.sleep(0, result=1)
        try:
            assert loop.run_sync(pending) is None
        finally:
            pending.close()
        loop.ensure()
        assert loop.loop is not None and loop.loop.is_running()
        original = loop.loop
        loop.ensure()
        assert loop.loop is original
        assert loop.run_sync(asyncio.sleep(0, result="ok")) == "ok"

        async def use_async_bridge():
            return await loop.run(asyncio.sleep(0, result=7))

        assert asyncio.run(use_async_bridge()) == 7
    finally:
        owner_loop = loop.loop
        loop.stop()
        if owner_loop is not None and not owner_loop.is_closed():
            owner_loop.close()
    assert loop.loop is None


def test_background_loop_run_requires_owner_loop():
    loop = BackgroundLoop()

    async def call():
        coro = asyncio.sleep(0)
        try:
            with pytest.raises(RuntimeError, match="Owner loop"):
                await loop.run(coro)
        finally:
            coro.close()

    asyncio.run(call())
