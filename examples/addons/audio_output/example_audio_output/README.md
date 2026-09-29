# Example audio-output provider

This `audio_output` Add-on generates a real playable WAV tone. It demonstrates provider settings, `prepare_output_path()` and the `speech(text)` contract without requiring a TTS account.

## Try it

Install and restart PyGPT, select **Example tone output** for Audio output, enable response speech and send a short message. PyGPT receives a generated WAV path and plays it through the normal audio-output flow. Change the tone frequency in settings to verify provider configuration.

Replace the tone generator with a real TTS SDK/API call while keeping the same return contract.
