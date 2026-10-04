# Example audio-input provider

This `audio_input` Add-on exercises the full provider path without external speech-recognition services. It accepts a WAV file, reads its duration with Python's standard library and returns a transcription-like text result. The bundled `locale/` directory shows that `provider.name` and settings added in `init_options()` are automatically translated through the provider Add-on domain.

## Try it

Install and restart PyGPT, select **Example WAV inspector** as the Audio input provider, then transcribe a WAV recording. The returned text includes the filename and duration. Change the provider prefix in plugin settings to verify that `init_options()` is wired correctly.

Replace `transcribe()` with your SDK/API call for a real speech-to-text provider.
