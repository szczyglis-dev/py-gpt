import sys
from types import ModuleType, SimpleNamespace

import pytest

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


def _patch_pydub(monkeypatch, audio):
    module = ModuleType("pydub")
    module.AudioSegment = SimpleNamespace(from_file=lambda path: audio)
    monkeypatch.setitem(sys.modules, "pydub", module)


def test_compute_envelope_maps_silence_and_full_scale(monkeypatch):
    audio = FakeAudio([0, 32767], 100)
    _patch_pydub(monkeypatch, audio)

    result = compute_envelope_from_file("audio.wav", chunk_ms=100)

    assert result[0] == 0.0
    assert result[1] == pytest.approx(100.0)


def test_compute_envelope_clamps_very_low_rms(monkeypatch):
    audio = FakeAudio([1], 100)
    _patch_pydub(monkeypatch, audio)
    assert compute_envelope_from_file("audio.wav", 100) == [0.0]
