from pygpt_net.provider.audio_output.base import BaseProvider

class ExampleAudioOutput(BaseProvider):
    def __init__(self):
        super().__init__()
        self.id = "example_audio_output"
        self.name = "External example audio output"
    def speech(self, text):
        return None
    def is_configured(self):
        return True
