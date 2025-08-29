#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.29 18:00:00                  #
# ================================================== #

import os
import wave
import base64

from .base import BaseProvider


class GoogleGenAITextToSpeech(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Google GenAI Text-to-Speech provider (Gemini TTS via API).

        :param args: args
        :param kwargs: kwargs
        """
        super(GoogleGenAITextToSpeech, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "google_genai_tts"
        self.name = "Google GenAI TTS"

        # Supported preview TTS models (fallback to flash if invalid)
        self.allowed_models = [
            "gemini-2.5-flash-preview-tts",
            "gemini-2.5-pro-preview-tts",
        ]

        # Prebuilt voice names exposed by Gemini TTS
        # Keep list in sync with official docs; fallback to "Puck" if invalid.
        self.allowed_voices = [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus",
            "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus",
            "Umbriel", "Algieba", "Despina", "Erinome", "Algenib",
            "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar",
            "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
            "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
        ]

    def init_options(self):
        """Initialize options"""
        # Keep option names consistent with the app style; simple text fields are enough.
        self.plugin.add_option(
            "google_genai_tts_model",
            type="text",
            value="gemini-2.5-flash-preview-tts",
            label="Model",
            tab="google_genai_tts",
            description="Specify Gemini TTS model, e.g.: gemini-2.5-flash-preview-tts or gemini-2.5-pro-preview-tts",
        )
        self.plugin.add_option(
            "google_genai_tts_voice",
            type="text",
            value="Kore",
            label="Voice",
            tab="google_genai_tts",
            description="Specify voice, e.g.: Puck, Kore, Charon, Leda, Zephyr... (case-sensitive)",
            urls={
                "Voices": "https://ai.google.dev/gemini-api/docs/speech-generation"
            },
        )

    def speech(self, text: str) -> str:
        """
        Text to speech synthesis using Google GenAI (Gemini TTS).

        :param text: text to synthesize
        :return: path to generated audio file
        """
        # Get pre-configured GenAI client
        client = self.plugin.window.core.api.google.get_client()

        # Resolve path where audio should be written
        output_file = self.plugin.output_file
        path = os.path.join(self.plugin.window.core.config.path, output_file)

        # Validate/select model
        model = self.plugin.get_option_value("google_genai_tts_model") or "gemini-2.5-flash-preview-tts"
        model = self._normalize_model_name(model)
        if model not in self.allowed_models:
            model = "gemini-2.5-flash-preview-tts"

        # Validate/select voice
        voice = self.plugin.get_option_value("google_genai_tts_voice") or "Kore"
        # if voice not in self.allowed_voices:
            # voice = "Kore"

        # Build generation config for audio modality + voice
        # Using explicit types for clarity and forward-compatibility
        try:
            from google.genai import types
        except Exception as ex:
            # Fail fast if SDK is missing or incompatible
            raise RuntimeError("google.genai SDK is not available. Please install/update Google GenAI SDK.") from ex

        gen_config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
            temperature=0.8,  # balanced default; keep configurable later if needed
        )

        # Perform TTS request
        response = client.models.generate_content(
            model=model,
            contents=text,
            config=gen_config,
        )

        # Extract PCM bytes from the first candidate/part
        pcm = self._extract_pcm_bytes(response)

        # Persist as standard WAV (PCM 16-bit, mono, 24 kHz)
        self._save_wav(path, pcm, channels=1, rate=24000, sample_width=2)

        return str(path)

    def _extract_pcm_bytes(self, response) -> bytes:
        """
        Extract PCM bytes from generate_content response.

        :param response: Google GenAI response object
        :return: raw PCM byte data
        """
        # Defensive extraction to support minor SDK variations
        data = None
        try:
            cand = response.candidates[0]
            part = cand.content.parts[0]
            if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                data = part.inline_data.data
        except Exception:
            pass

        if data is None:
            # Some SDK builds may return base64 str; try resolving alternative layout
            try:
                parts = getattr(response, "candidates", [])[0].content.parts
                for p in parts:
                    if getattr(p, "inline_data", None) and getattr(p.inline_data, "data", None):
                        data = p.inline_data.data
                        break
            except Exception:
                pass

        if data is None:
            raise RuntimeError("No audio data returned by Gemini TTS response.")

        # Normalize to raw bytes
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, str):
            # Fallback: treat as base64-encoded PCM
            return base64.b64decode(data)

        # Last resort: try bytes() cast
        try:
            return bytes(data)
        except Exception as ex:
            raise RuntimeError("Unsupported audio payload type returned by Gemini TTS.") from ex

    def _save_wav(
            self,
            filename: str,
            pcm_bytes: bytes,
            channels: int = 1,
            rate: int = 24000,
            sample_width: int = 2
    ):
        """
        Save raw PCM bytes to a WAV file.

        :param filename: output WAV file path
        :param pcm_bytes: raw PCM byte data
        :param channels: number of audio channels (1=mono, 2=stereo)
        :param rate: sample rate in Hz (e.g., 24000)
        :param sample_width: sample width in bytes (e.g., 2 for 16-bit)
        """
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Write PCM payload as WAV
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)  # bytes per sample (2 -> 16-bit)
            wf.setframerate(rate)
            wf.writeframes(pcm_bytes)

    def _normalize_model_name(self, model: str) -> str:
        """
        Normalize model id (strip optional 'models/' prefix).

        :param model: model id
        """
        try:
            return model.split("/")[-1]
        except Exception:
            return model

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        api_key = self.plugin.window.core.config.get("api_key_google")
        return api_key is not None and api_key != ""

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return "Google GenAI API key is not set yet. Please configure it in settings."