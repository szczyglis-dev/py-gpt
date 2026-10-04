"""Duration checks shared by microphone backends."""

MIN_RECORDING_MS = 100


def has_minimum_audio(frames, rate, channels, sample_width):
    """Check PCM duration independently of callback chunk sizes."""
    bytes_per_second = rate * channels * sample_width
    return (bytes_per_second > 0
            and sum(len(frame) for frame in frames) * 1000
            >= bytes_per_second * MIN_RECORDING_MS)
