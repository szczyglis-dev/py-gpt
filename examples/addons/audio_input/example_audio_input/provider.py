"""Runnable audio-input provider example using only the Python standard library."""

import os
import wave

from pygpt_net.provider.audio_input.base import BaseProvider


class ExampleAudioInput(BaseProvider):
    def __init__(self):
        super().__init__()
        self.id = "example_audio_input"
        self.name = "Example WAV inspector"

    def init_options(self):
        self.plugin.add_option(
            "example_audio_prefix",
            type="text",
            value="Example transcription",
            label="Example transcription prefix",
            description="Prefix returned by the tutorial provider.",
            tab=self.id,
        )

    def transcribe(self, path):
        # This is intentionally not speech recognition. It proves the complete
        # provider path by reading a WAV file and returning useful text.
        duration = None
        try:
            with wave.open(path, "rb") as wav:
                rate = wav.getframerate() or 1
                duration = wav.getnframes() / float(rate)
        except (wave.Error, OSError):
            pass

        prefix = self.plugin.get_option_value("example_audio_prefix") or "Example transcription"
        name = os.path.basename(path)
        if duration is None:
            return f"{prefix}: received {name}."
        return f"{prefix}: received {name}, WAV duration {duration:.2f} s."

    def is_configured(self):
        return True
