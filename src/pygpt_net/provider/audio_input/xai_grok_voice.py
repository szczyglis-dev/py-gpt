#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 20:00:00                  #
# ================================================== #

import asyncio
import base64
import json
import os
import queue
import subprocess
import threading
from typing import Optional

from .base import BaseProvider


class XAIGrokVoiceAudioInput(BaseProvider):
    PROMPT_TRANSCRIBE = (
        "You are a speech-to-text transcriber. "
        "Return only the verbatim transcript as plain text. "
        "Do not add any explanations, timestamps, labels or formatting."
    )

    def __init__(self, *args, **kwargs):
        """
        xAI Grok Voice Agent-based audio transcription provider (via WebSocket API).

        :param args: args
        :param kwargs: kwargs
        """
        super(XAIGrokVoiceAudioInput, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "xai_grok_voice"
        self.name = "xAI Grok Voice"

    def init_options(self):
        """Initialize options"""
        # Model is implicit for the realtime Voice Agent; keep options focused on audio and behavior
        self.plugin.add_option(
            "xai_voice_audio_sample_rate",
            type="text",
            value="16000",
            label="Sample rate (Hz)",
            tab="xai_grok_voice",
            description="PCM sample rate for input, e.g., 16000 or 24000",
        )
        self.plugin.add_option(
            "xai_voice_system_prompt",
            type="textarea",
            value=self.PROMPT_TRANSCRIBE,
            label="System Prompt",
            tab="xai_grok_voice",
            description="System prompt to guide the transcription output",
            tooltip="System prompt for transcription",
            persist=True,
        )
        self.plugin.add_option(
            "xai_voice_region",
            type="text",
            value="",
            label="Region (optional)",
            tab="xai_grok_voice",
            description="Regional endpoint like us-east-1; leave empty to use the global endpoint",
        )
        self.plugin.add_option(
            "xai_voice_chunk_ms",
            type="text",
            value="200",
            label="Chunk size (ms)",
            tab="xai_grok_voice",
            description="Size of audio chunks to send over WebSocket",
        )

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription using xAI Grok Voice Agent (WebSocket).

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        # Ensure xAI client is initialized in core (keeps auth/config consistent with the app)
        # We do not rely on its methods for WebSocket, but we respect the app's initialization order
        try:
            _ = self.plugin.window.core.api.xai.get_client()
        except Exception:
            # Client not strictly required for WebSocket usage; continue if available credentials are set
            pass

        api_key = self._get_api_key()
        if not api_key:
            raise RuntimeError("xAI API key is not set. Please configure it in settings.")

        # Resolve endpoint (optionally regionalized)
        region = (self.plugin.get_option_value("xai_voice_region") or "").strip()
        host = f"{region}.api.x.ai" if region else "api.x.ai"
        ws_uri = f"wss://{host}/v1/realtime"

        # Read options
        prompt = self.plugin.get_option_value("xai_voice_system_prompt") or self.PROMPT_TRANSCRIBE
        sr_opt = str(self.plugin.get_option_value("xai_voice_audio_sample_rate") or "16000").strip()
        try:
            sample_rate = max(8000, int(sr_opt))
        except Exception:
            sample_rate = 16000

        chunk_ms_opt = str(self.plugin.get_option_value("xai_voice_chunk_ms") or "200").strip()
        try:
            chunk_ms = max(20, int(chunk_ms_opt))
        except Exception:
            chunk_ms = 200

        # Compute chunk size for 16-bit mono PCM
        bytes_per_second = sample_rate * 2  # 1 channel * 2 bytes
        chunk_size = max(4096, int(bytes_per_second * (chunk_ms / 1000.0)))

        # Run async websocket pipeline in an isolated thread/loop to avoid interfering with the UI loop
        result_queue: queue.Queue[str] = queue.Queue()

        def _runner():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                text = loop.run_until_complete(
                    self._transcribe_async(
                        ws_uri=ws_uri,
                        api_key=api_key,
                        path=path,
                        sample_rate=sample_rate,
                        chunk_size=chunk_size,
                        system_prompt=prompt,
                    )
                )
                result_queue.put(text or "")
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()

        return result_queue.get() if not result_queue.empty() else ""

    async def _transcribe_async(
        self,
        ws_uri: str,
        api_key: str,
        path: str,
        sample_rate: int,
        chunk_size: int,
        system_prompt: str,
    ) -> str:
        """
        Connects to xAI Voice Agent realtime WebSocket and streams audio for transcription.
        Returns the final transcript text.
        """
        try:
            import websockets  # type: ignore
            from websockets.asyncio.client import ClientConnection  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "The 'websockets' package is required for xAI Voice transcription. "
                "Please install it in your environment."
            ) from e

        transcript: Optional[str] = None

        async with websockets.connect(
            uri=ws_uri,
            ssl=True,
            open_timeout=30,
            close_timeout=10,
            additional_headers={"Authorization": f"Bearer {api_key}"},
            max_size=None,
        ) as ws:  # type: ClientConnection
            # Configure session to match our audio and enforce transcription-only behavior
            session_config = {
                "type": "session.update",
                "session": {
                    "instructions": system_prompt,
                    # We are only transcribing; disable server VAD and commit manually as a single turn
                    "turn_detection": {"type": None},
                    "audio": {
                        "input": {"format": {"type": "audio/pcm", "rate": sample_rate}},
                        # Output audio not needed; keep default
                    },
                },
            }
            await ws.send(json.dumps(session_config))

            # Stream the audio
            is_wav = path.lower().endswith((".wav", ".wave"))
            if is_wav:
                # Fast path for WAV (PCM or otherwise; convert to mono s16le at desired rate)
                pcm_bytes, duration_s = self._decode_wav_to_pcm_s16le(path, sample_rate)
                for i in range(0, len(pcm_bytes), chunk_size):
                    chunk = pcm_bytes[i : i + chunk_size]
                    if not chunk:
                        break
                    await ws.send(
                        json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": base64.b64encode(chunk).decode("ascii"),
                            }
                        )
                    )
            else:
                # Generic path via ffmpeg to decode to mono s16le at sample_rate
                duration_s = None  # unknown
                await self._stream_via_ffmpeg(ws, path, sample_rate, chunk_size)

            # Commit a single user message from the accumulated audio buffer
            await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # Wait for transcript events
            # Use a dynamic timeout: at least 30s; more for longer audio
            base_timeout = 30.0
            if duration_s is not None:
                # allow ~2x audio length + base safety window
                timeout_s = min(600.0, max(base_timeout, duration_s * 2.0 + 10.0))
            else:
                timeout_s = 120.0

            try:
                transcript = await self._await_transcript(ws, timeout=timeout_s)
            except asyncio.TimeoutError:
                # Try to salvage from any conversation.item.added events cached in the loop
                pass

        return transcript or ""

    async def _await_transcript(self, ws, timeout: float) -> Optional[str]:
        """
        Waits for either:
          - conversation.item.input_audio_transcription.completed (preferred)
          - conversation.item.added with content.type == 'input_audio' (fallback)
        """
        end_time = asyncio.get_event_loop().time() + timeout
        pending_fallback: Optional[str] = None

        while True:
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise asyncio.TimeoutError("Timed out waiting for xAI transcription result.")

            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                raise
            except Exception:
                break

            try:
                event = json.loads(msg)
            except Exception:
                continue

            etype = event.get("type", "")
            if etype == "conversation.item.input_audio_transcription.completed":
                # Preferred final transcript
                return event.get("transcript") or ""
            elif etype == "conversation.item.added":
                # Fallback: some responses include the inline transcript in the added user item
                item = event.get("item") or {}
                if item.get("role") == "user":
                    for c in item.get("content", []):
                        if isinstance(c, dict) and c.get("type") == "input_audio" and "transcript" in c:
                            pending_fallback = c.get("transcript") or pending_fallback
            elif etype == "response.done":
                # If server signals end of turn and we have a fallback transcript, return it
                if pending_fallback:
                    return pending_fallback

    async def _stream_via_ffmpeg(self, ws, path: str, sample_rate: int, chunk_size: int):
        """
        Uses ffmpeg to decode arbitrary input to mono s16le at sample_rate and streams chunks.
        """
        cmd = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            path,
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "pipe:1",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "ffmpeg not found. Install ffmpeg or provide WAV input for xAI transcription."
            ) from e

        try:
            while True:
                chunk = await proc.stdout.read(chunk_size)
                if not chunk:
                    break
                await ws.send(
                    json.dumps(
                        {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(chunk).decode("ascii"),
                        }
                    )
                )
        finally:
            try:
                await proc.wait()
            except Exception:
                pass

    def _decode_wav_to_pcm_s16le(self, path: str, target_rate: int):
        """
        Decodes a WAV file to mono 16-bit PCM at target_rate.
        Returns (bytes, duration_seconds).
        """
        import wave
        import audioop

        with wave.open(path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        # Convert to mono if needed
        if n_channels > 1:
            raw = audioop.tomono(raw, sampwidth, 1, 1)

        # Convert sample width to 16-bit
        if sampwidth != 2:
            raw = audioop.lin2lin(raw, sampwidth, 2)

        # Resample if needed
        if framerate != target_rate:
            raw, _ = audioop.ratecv(raw, 2, 1, framerate, target_rate, None)
            framerate = target_rate

        duration_s = len(raw) / float(target_rate * 2)  # mono, 16-bit
        return raw, duration_s

    def _get_api_key(self) -> Optional[str]:
        """
        Resolve xAI API key from the app's configuration.
        """
        # Prefer explicit xAI key if present
        key = self.plugin.window.core.config.get("api_key_xai")
        if key:
            return key

        # Optional: try environment variable for parity with SDKs
        return os.getenv("XAI_API_KEY")

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        api_key = self._get_api_key()
        return api_key is not None and api_key != ""

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return "xAI API key is not set yet. Please configure it in settings."