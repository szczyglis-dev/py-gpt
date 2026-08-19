#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT audio-output provider tutorial               #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

from pygpt_net.provider.audio_output.base import BaseProvider


class ExampleAudioOutput(BaseProvider):
    """Minimal text-to-speech provider using the OpenAI API as an example."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_audio_output"  # must be unique
        self.name = "Example audio output (OpenAI TTS)"

    def init_options(self):
        """Declare provider-specific settings shown in the Audio Output plugin."""
        self.plugin.add_option(
            "example_model",
            type="text",
            value="tts-1",
            label="TTS model",
            tab=self.id,
            description="Text-to-speech model sent to the provider.",
        )
        self.plugin.add_option(
            "example_voice",
            type="text",
            value="alloy",
            label="Voice",
            tab=self.id,
            description="Voice name supported by the selected TTS model.",
        )

    def speech(self, text: str) -> str:
        """Generate speech and return the path to the generated audio file.

        Important: use `prepare_output_path()` instead of a fixed filename.
        PyGPT stores generated TTS files below `workdir/tmp/audio_output`, gives
        each file a unique name, and rotates old files. Unique files also avoid
        Windows file-lock problems while audio is still being played.
        """
        client = self.plugin.window.core.api.openai.get_client()
        path = self.prepare_output_path(extension="mp3")

        response = client.audio.speech.create(
            model=self.plugin.get_option_value("example_model"),
            voice=self.plugin.get_option_value("example_voice"),
            input=text,
        )
        response.stream_to_file(path)
        return str(path)

    def is_configured(self) -> bool:
        api_key = self.plugin.window.core.config.get("api_key")
        return bool(api_key)

    def get_config_message(self) -> str:
        return "OpenAI API key is not configured. Set it in Config -> Settings -> API Keys."
