#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 20:00:00                  #
# ================================================== #

import base64
import io
import wave
from typing import Optional, Tuple

from google.genai.types import Part
from pygpt_net.core.bridge.context import MultimodalContext


class Audio:
    def __init__(self, window=None):
        """
        Audio helpers for Google GenAI.
        - Build audio input parts for requests
        - Convert Google PCM output to WAV (base64) for UI compatibility

        :param window: Window instance
        """
        self.window = window

    # ---------- INPUT (user -> model) ----------

    def build_part(
            self,
            multimodal_ctx: Optional[MultimodalContext]
    ) -> Optional[Part]:
        """
        Build audio Part from multimodal context (inline bytes).

        :param multimodal_ctx: MultimodalContext
        :return: Part or None
        """
        if not multimodal_ctx or not multimodal_ctx.is_audio_input or not multimodal_ctx.audio_data:
            return None
        audio_format = (multimodal_ctx.audio_format or "wav").lower()
        mime = f"audio/{audio_format}"
        return Part.from_bytes(data=multimodal_ctx.audio_data, mime_type=mime)

    # ---------- OUTPUT (model -> UI) ----------

    def extract_first_audio_part(
            self,
            response
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Extract first audio inline_data from a non-streaming response.

        :param response: Google response object
        :return: (audio_bytes, mime_type) or (None, None)
        """
        try:
            candidates = getattr(response, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    inline = getattr(p, "inline_data", None)
                    if not inline:
                        continue
                    mime = (getattr(inline, "mime_type", "") or "").lower()
                    if not mime.startswith("audio/"):
                        continue
                    data = getattr(inline, "data", None)
                    audio_bytes = self._ensure_bytes(data)
                    if audio_bytes:
                        return audio_bytes, mime
        except Exception:
            pass
        return None, None

    def pcm16_to_wav_base64(
            self,
            pcm_bytes: bytes,
            rate: int = 24000,
            channels: int = 1,
            sample_width: int = 2
    ) -> str:
        """
        Wrap raw PCM16 mono @ 24kHz into WAV and return base64-encoded payload.

        :param pcm_bytes: Raw PCM16 bytes
        :param rate: Sample rate (Hz), default 24000 for Google TTS
        :param channels: Channels, default 1
        :param sample_width: Bytes per sample, default 2 for PCM16
        :return: Base64-encoded WAV
        """
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_bytes)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    @staticmethod
    def _ensure_bytes(data) -> Optional[bytes]:
        """
        Return raw bytes from inline_data.data (bytes or base64 string).

        :param data: bytes or base64 string
        :return: bytes or None
        """
        try:
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            if isinstance(data, str):
                return base64.b64decode(data)
        except Exception:
            return None
        return None