from types import SimpleNamespace

import pytest

import pygpt_net.core.audio.backend.native.native as native_module
import pygpt_net.core.audio.backend.pyaudio.pyaudio as pyaudio_module
import pygpt_net.core.audio.backend.pygame.pygame as pygame_module
from pygpt_net.core.audio.backend.native.native import NativeBackend
from pygpt_net.core.audio.backend.pyaudio.pyaudio import PyaudioBackend
from pygpt_net.core.audio.backend.pygame.pygame import PygameBackend


@pytest.mark.parametrize("backend_cls", [NativeBackend, PyaudioBackend, PygameBackend])
def test_audio_backends_basic_state_helpers(backend_cls):
    backend = backend_cls(window=None)
    callback = lambda: None

    backend.set_mode("control")
    backend.set_repeat_callback(callback)
    backend.set_loop(True)
    backend.set_path("/tmp/audio.wav")

    assert backend.mode == "control"
    assert backend.stop_callback is callback
    assert backend.loop is True
    assert backend.path == "/tmp/audio.wav"
    assert backend.has_frames() is False

    backend.frames = [b"x"] * backend.MIN_FRAMES
    assert backend.has_frames() is True
    assert backend.has_min_frames() is True


@pytest.mark.parametrize("backend_cls", [NativeBackend, PyaudioBackend, PygameBackend])
def test_audio_backends_reject_non_callable_repeat_callback(backend_cls):
    backend = backend_cls(window=None)
    with pytest.raises(ValueError, match="callable"):
        backend.set_repeat_callback("not-callable")


def test_audio_backends_native_and_pyaudio_emit_output_volume(monkeypatch):
    for module, backend_cls in ((native_module, NativeBackend), (pyaudio_module, PyaudioBackend)):
        backend = backend_cls(window=None)
        backend._rt_signals = object()
        event = object()
        emitted = []
        monkeypatch.setattr(module, "build_output_volume_event", lambda value, _event=event: _event)
        monkeypatch.setattr(module, "safe_emit", lambda source, name, payload: emitted.append((source, name, payload)) or True)

        backend._emit_output_volume(37)

        assert emitted == [(backend._rt_signals, "response", event)]


def test_audio_backends_pygame_emits_realtime_input_on_qt_timer(monkeypatch):
    backend = PygameBackend(window=None)
    backend._rt_signals = object()
    event = object()
    emitted = []

    monkeypatch.setattr(pygame_module, "build_rt_input_delta_event", lambda **kwargs: event)
    monkeypatch.setattr(pygame_module, "safe_emit", lambda source, name, payload: emitted.append((source, name, payload)) or True)
    monkeypatch.setattr(
        pygame_module,
        "QTimer",
        SimpleNamespace(singleShot=lambda delay, callback: callback()),
    )

    backend._emit_rt_input_delta(b"abc", final=True)

    assert emitted == [(backend._rt_signals, "response", event)]
