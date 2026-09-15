from types import SimpleNamespace

import pytest

import pygpt_net.core.audio.backend.shared.envelope as envelope_module
from pygpt_net.core.audio.backend.shared.envelope import compute_envelope_from_file


class FakeAudio:
    def __init__(self, rms_values, chunk_ms):
        self.rms_values = rms_values
        self.chunk_ms = chunk_ms

    def __len__(self):
        return len(self.rms_values) * self.chunk_ms

    def __getitem__(self, key):
        idx = key.start // self.chunk_ms
        return SimpleNamespace(rms=self.rms_values[idx])


def test_compute_envelope_maps_silence_and_full_scale(monkeypatch):
    audio = FakeAudio([0, 32767], 100)
    monkeypatch.setattr(envelope_module.AudioSegment, "from_file", lambda path: audio)

    result = compute_envelope_from_file("audio.wav", chunk_ms=100)

    assert result[0] == 0.0
    assert result[1] == pytest.approx(100.0)


def test_compute_envelope_clamps_very_low_rms(monkeypatch):
    audio = FakeAudio([1], 100)
    monkeypatch.setattr(envelope_module.AudioSegment, "from_file", lambda path: audio)
    assert compute_envelope_from_file("audio.wav", 100) == [0.0]
