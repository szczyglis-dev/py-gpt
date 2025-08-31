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

import io
import math
import os
import wave
import audioop
from array import array
import struct
from typing import Optional, Tuple, List

DEFAULT_24K = 24000

def coerce_to_pcm16_mono(data: bytes, fmt: Optional[str], rate_hint: Optional[int], fallback_rate: int = DEFAULT_24K) -> Tuple[int, int, bytes]:
    """
    Convert input audio (PCM16 raw or WAV) to PCM16 mono bytes. Float WAV is treated as raw (best effort).
    Returns (sample_rate, channels=1, pcm16_bytes).
    """
    if not data:
        return fallback_rate, 1, b""
    fmt = (fmt or "").lower().strip()
    if fmt in ("pcm16", "pcm", "raw"):
        sr = int(rate_hint) if rate_hint else fallback_rate
        return sr, 1, data

    # WAV path
    try:
        with wave.open(io.BytesIO(data), "rb") as wf:
            sr = wf.getframerate() or fallback_rate
            ch = wf.getnchannels() or 1
            sw = wf.getsampwidth() or 2
            frames = wf.readframes(wf.getnframes())

        if sw != 2:
            frames = audioop.lin2lin(frames, sw, 2)
        if ch == 2:
            frames = audioop.tomono(frames, 2, 0.5, 0.5)
        elif ch != 1:
            frames = audioop.tomono(frames, 2, 1.0, 0.0)

        return sr, 1, frames
    except Exception:
        sr = int(rate_hint) if rate_hint else fallback_rate
        return sr, 1, data

def float32_to_int16_bytes(b: bytes) -> bytes:
    """Convert little-endian float32 PCM [-1.0, 1.0] to int16 PCM."""
    if not b:
        return b""
    try:
        arr = array("f")
        arr.frombytes(b)
        if struct.unpack('<I', struct.pack('=I', 1))[0] != 1:  # fallback if non-little
            arr.byteswap()
        out = array("h", (max(-32768, min(32767, int(round(x * 32767.0)))) for x in arr))
        return out.tobytes()
    except Exception:
        try:
            n = len(b) // 4
            vals = struct.unpack("<" + "f" * n, b[: n * 4])
            out = array("h", (max(-32768, min(32767, int(round(x * 32767.0)))) for x in vals))
            return out.tobytes()
        except Exception:
            return b""

def parse_wav_fmt(data: bytes) -> Optional[dict]:
    """Minimal WAV fmt chunk parser to detect float/int format."""
    try:
        if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
            return None
        p = 12
        while p + 8 <= len(data):
            cid = data[p:p+4]
            sz = int.from_bytes(data[p+4:p+8], "little", signed=False)
            p += 8
            if cid == b"fmt ":
                fmtb = data[p:p+sz]
                if len(fmtb) < 16:
                    return None
                format_tag = int.from_bytes(fmtb[0:2], "little")
                channels = int.from_bytes(fmtb[2:4], "little")
                sample_rate = int.from_bytes(fmtb[4:8], "little")
                bits_per_sample = int.from_bytes(fmtb[14:16], "little")
                sub_tag = None
                if format_tag == 65534 and sz >= 40:  # WAVE_FORMAT_EXTENSIBLE
                    sub_tag = int.from_bytes(fmtb[24:26], "little", signed=False)
                return {
                    "format_tag": format_tag,
                    "channels": channels,
                    "sample_rate": sample_rate,
                    "bits_per_sample": bits_per_sample,
                    "subformat_tag": sub_tag,
                }
            p += (sz + 1) & ~1
        return None
    except Exception:
        return None

def to_pcm16_mono(data: bytes, fmt: Optional[str], rate_hint: Optional[int], target_rate: int) -> Tuple[bytes, int]:
    """
    Normalize any input audio (RAW/WAV, int/float) to PCM16 mono at target_rate.
    Returns (pcm16_bytes, target_rate).
    """
    if not data:
        return b"", target_rate

    fmt = (fmt or "").lower().strip()
    if fmt in ("pcm16", "pcm", "raw"):
        src_rate = int(rate_hint) if rate_hint else target_rate
        pcm16 = data
        if src_rate != target_rate:
            try:
                pcm16, _ = audioop.ratecv(pcm16, 2, 1, src_rate, target_rate, None)
            except Exception:
                return b"", target_rate
        return pcm16, target_rate

    # WAV path with float support
    try:
        fmt_info = parse_wav_fmt(data)
        with wave.open(io.BytesIO(data), "rb") as wf:
            sr = wf.getframerate() or target_rate
            ch = wf.getnchannels() or 1
            sw = wf.getsampwidth() or 2
            frames = wf.readframes(wf.getnframes())

        format_tag = (fmt_info or {}).get("format_tag", 1)
        bits_per_sample = (fmt_info or {}).get("bits_per_sample", sw * 8)

        # float32 -> int16
        if format_tag == 3 or ((format_tag == 65534) and (fmt_info or {}).get("subformat_tag") == 3):
            frames16 = float32_to_int16_bytes(frames)
        else:
            if sw != 2:
                frames16 = audioop.lin2lin(frames, sw, 2)
            else:
                frames16 = frames

        # mixdown to mono
        if ch == 2:
            try:
                frames16 = audioop.tomono(frames16, 2, 0.5, 0.5)
            except Exception:
                frames16 = frames16[0::2] + b""
        elif ch != 1:
            try:
                frames16 = audioop.tomono(frames16, 2, 1.0, 0.0)
            except Exception:
                pass

        # resample
        if sr != target_rate:
            try:
                frames16, _ = audioop.ratecv(frames16, 2, 1, sr, target_rate, None)
            except Exception:
                return b"", target_rate

        return frames16, target_rate
    except Exception:
        return b"", target_rate

def resample_pcm16_mono(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    if src_rate == dst_rate or not pcm:
        return pcm
    try:
        out, _ = audioop.ratecv(pcm, 2, 1, src_rate, dst_rate, None)
        return out
    except Exception:
        return pcm

def iter_pcm_chunks(pcm: bytes, sr: int, ms: int = 50) -> List[bytes]:
    """Split PCM16 mono stream into ~ms byte chunks."""
    b_per_ms = int(sr * 2 / 1000)
    n = max(b_per_ms * ms, 1)
    return [pcm[i:i + n] for i in range(0, len(pcm), n)]

def dump_wav(path: str, sample_rate: int, pcm16_mono: bytes):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass
    try:
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(int(sample_rate))
            wf.writeframes(pcm16_mono)
    except Exception:
        pass

def pcm16_stats(pcm16_mono: bytes, sample_rate: int) -> dict:
    try:
        n_samp = len(pcm16_mono) // 2
        dur = n_samp / float(sample_rate or 1)
        rms = audioop.rms(pcm16_mono, 2)
        peak = audioop.max(pcm16_mono, 2) if pcm16_mono else 0
        try:
            avg = audioop.avg(pcm16_mono, 2)
        except Exception:
            avg = 0
        dbfs = (-999.0 if rms == 0 else 20.0 * math.log10(rms / 32768.0))
        return {"duration_s": dur, "samples": n_samp, "rms": rms, "peak": peak, "dc_offset": avg, "dbfs": dbfs}
    except Exception:
        return {}