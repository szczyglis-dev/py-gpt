# provider/audio_output/xai_tts.py

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
import threading
import wave
from typing import Optional, Tuple

from .base import BaseProvider


class XAITextToSpeech(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        xAI Grok Voice Agent text-to-speech provider (via WebSocket).

        :param args: args
        :param kwargs: kwargs
        """
        super(XAITextToSpeech, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "xai_tts"
        self.name = "xAI TTS"

        self.supported_voices = ["Ara", "Rex", "Sal", "Eve", "Leo"]

    def init_options(self):
        """Initialize options"""
        self.plugin.add_option(
            "xai_tts_voice",
            type="text",
            value="Ara",
            label="Voice",
            tab="xai_tts",
            description="Specify xAI Grok Voice name (Ara, Rex, Sal, Eve, Leo)",
            urls={"Voices": "https://docs.x.ai/docs/guides/voice/agent"},
        )
        self.plugin.add_option(
            "xai_tts_sample_rate",
            type="text",
            value="24000",
            label="Sample rate (Hz)",
            tab="xai_tts",
            description="PCM sample rate for output audio, e.g., 16000 or 24000",
        )
        self.plugin.add_option(
            "xai_tts_instructions",
            type="textarea",
            value="You are a neutral TTS voice. Speak clearly and read the text verbatim.",
            label="System Prompt",
            tab="xai_tts",
            description="System prompt to guide TTS style",
            tooltip="System prompt for voice output",
            persist=True,
        )
        self.plugin.add_option(
            "xai_tts_file_container",
            type="text",
            value="wav",
            label="File container",
            tab="xai_tts",
            description="wav or raw",
        )
        self.plugin.add_option(
            "xai_tts_region",
            type="text",
            value="",
            label="Region (optional)",
            tab="xai_tts",
            description="Regional endpoint like us-east-1; leave empty for global",
        )

    def speech(self, text: str) -> str:
        """
        Speech text to audio

        :param text: text to speech
        :return: path to generated audio file
        """
        try:
            _ = self.plugin.window.core.api.xai.get_client()
        except Exception:
            pass

        api_key = self._get_api_key()
        if not api_key:
            raise RuntimeError("xAI API key is not set. Please configure it in settings.")

        voice = (self.plugin.get_option_value("xai_tts_voice") or "Ara").strip() or "Ara"
        sr_opt = str(self.plugin.get_option_value("xai_tts_sample_rate") or "24000").strip()
        try:
            sample_rate = max(8000, int(sr_opt))
        except Exception:
            sample_rate = 24000
        instructions = self.plugin.get_option_value("xai_tts_instructions") or ""
        container = (self.plugin.get_option_value("xai_tts_file_container") or "wav").strip().lower()
        if container not in ("wav", "raw"):
            container = "wav"

        region = (self.plugin.get_option_value("xai_tts_region") or "").strip()
        host = f"{region}.api.x.ai" if region else "api.x.ai"
        ws_uri = f"wss://{host}/v1/realtime"

        base_dir = self.plugin.window.core.config.path
        default_name = getattr(self.plugin, "output_file", "output.wav")
        out_path = os.path.join(base_dir, default_name)
        out_path = self._ensure_extension(out_path, ".wav" if container == "wav" else ".raw")

        result_queue: queue.Queue[Tuple[bool, Optional[str], Optional[bytes]]] = queue.Queue()

        def _runner():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                ok, err, pcm = loop.run_until_complete(
                    self._synthesize_async(
                        ws_uri=ws_uri,
                        api_key=api_key,
                        input_text=text,
                        voice=voice,
                        sample_rate=sample_rate,
                        instructions=instructions,
                    )
                )
                result_queue.put((ok, err, pcm))
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join()

        ok, err, pcm_bytes = result_queue.get() if not result_queue.empty() else (False, "Unknown error", None)
        if not ok or not pcm_bytes:
            raise RuntimeError(err or "xAI TTS failed.")

        if container == "wav":
            self._write_wav(out_path, sample_rate, pcm_bytes)
        else:
            with open(out_path, "wb") as f:
                f.write(pcm_bytes)

        return str(out_path)

    async def _synthesize_async(
        self,
        ws_uri: str,
        api_key: str,
        input_text: str,
        voice: str,
        sample_rate: int,
        instructions: str,
    ) -> Tuple[bool, Optional[str], Optional[bytes]]:
        """
        Connects to xAI Voice Agent realtime WebSocket and requests audio for the given text.
        Returns (ok, error_message, pcm_bytes).
        """
        try:
            import websockets  # type: ignore
            from websockets.asyncio.client import ClientConnection  # type: ignore
        except Exception:
            return False, (
                "The 'websockets' package is required for xAI TTS. Please install it in your environment."
            ), None

        audio_buf = bytearray()
        transcript_buf = []

        try:
            async with websockets.connect(
                uri=ws_uri,
                ssl=True,
                open_timeout=30,
                close_timeout=10,
                additional_headers={"Authorization": f"Bearer {api_key}"},
                max_size=None,
            ) as ws:  # type: ClientConnection
                session_config = {
                    "type": "session.update",
                    "session": {
                        "instructions": instructions,
                        "voice": voice,
                        "turn_detection": {"type": None},
                        "audio": {
                            "input": {"format": {"type": "audio/pcm", "rate": sample_rate}},
                            "output": {"format": {"type": "audio/pcm", "rate": sample_rate}},
                        },
                    },
                }
                await ws.send(json.dumps(session_config))

                await ws.send(
                    json.dumps(
                        {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": input_text}],
                            },
                        }
                    )
                )

                await ws.send(
                    json.dumps(
                        {
                            "type": "response.create",
                            "response": {
                                "modalities": ["text", "audio"],
                            },
                        }
                    )
                )

                end_time = asyncio.get_event_loop().time() + 90.0
                got_any_audio = False

                while True:
                    remaining = end_time - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        return False, "Timed out waiting for xAI audio output.", None
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        return False, "Timed out waiting for xAI audio output.", None
                    except Exception as e:
                        return False, f"WebSocket error: {e}", None

                    try:
                        event = json.loads(msg)
                    except Exception:
                        continue

                    etype = event.get("type", "")

                    if etype == "response.output_audio.delta":
                        # xAI sends base64 audio in the 'delta' field
                        chunk_b64 = event.get("delta")
                        if chunk_b64:
                            try:
                                audio_buf.extend(base64.b64decode(chunk_b64))
                                got_any_audio = True
                            except Exception:
                                pass
                    elif etype == "response.output_audio_transcript.delta":
                        # Collect transcript (not used for file, helpful for debugging)
                        delta_txt = event.get("delta")
                        if delta_txt:
                            transcript_buf.append(delta_txt)
                    elif etype == "response.output_audio.done":
                        # Wait for response.done to ensure turn completion
                        continue
                    elif etype == "response.done":
                        break
                    elif etype == "response.error":
                        return False, event.get("message") or "xAI TTS error.", None

                if not got_any_audio:
                    # Provide a more helpful error if we at least got transcript
                    if transcript_buf:
                        return False, "Empty audio from xAI TTS, but transcript was returned.", None
                    return False, "Empty audio from xAI TTS.", None

                return True, None, bytes(audio_buf)
        except Exception as e:
            return False, f"WebSocket connection failed: {e}", None

    def _write_wav(self, path: str, sample_rate: int, pcm_bytes: bytes):
        """
        Writes PCM16LE mono samples into a WAV container.
        """
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)

    def _ensure_extension(self, path: str, desired_ext: str) -> str:
        """
        Replaces the file extension with desired_ext.
        """
        root, _ = os.path.splitext(path)
        return root + desired_ext

    def _get_api_key(self) -> Optional[str]:
        """
        Resolve xAI API key from the app's configuration or environment.
        """
        key = self.plugin.window.core.config.get("api_key_xai")
        if key:
            return key
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