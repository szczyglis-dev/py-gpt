from pygpt_net.provider.audio_input.base import BaseProvider

class ExampleAudioInput(BaseProvider):
    def __init__(self):
        super().__init__()
        self.id = "example_audio_input"
        self.name = "External example audio input"
    def transcribe(self, path):
        return "Example transcription"
    def is_configured(self):
        return True
