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

    backend.frames = [b"x"]
    assert backend.has_frames() is True


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


@pytest.mark.parametrize("backend_cls", [NativeBackend, PyaudioBackend, PygameBackend])
def test_capture_start_reports_failed_open(backend_cls, monkeypatch):
    backend = backend_cls(window=None)
    monkeypatch.setattr(backend, "init", lambda: None)
    monkeypatch.setattr(backend, "prepare_device", lambda: None)
    monkeypatch.setattr(backend, "setup_audio_input", lambda: None)
    backend.selected_device = 1

    assert backend.start() is False
    assert not backend.has_source()


@pytest.mark.parametrize("fail_start", [False, True])
def test_pyaudio_opens_once_and_activates_before_first_callback(monkeypatch, fail_start):
    from unittest.mock import Mock

    backend = PyaudioBackend(window=None)
    monkeypatch.setattr(backend, "init", lambda: None)
    monkeypatch.setattr(backend, "prepare_device", lambda: None)
    backend.selected_device = 7
    stream = Mock()
    backend.pyaudio_instance = Mock()
    backend.pyaudio_instance.open.return_value = stream

    def start_stream():
        assert backend._input_active
        assert backend.start_time > 0
        if fail_start:
            raise OSError("Device unavailable")

    stream.start_stream.side_effect = start_stream
    assert backend.start() is (not fail_start)
    backend.pyaudio_instance.open.assert_called_once()
    options = backend.pyaudio_instance.open.call_args.kwargs
    assert options["start"] is False
    assert options["input_device_index"] == 7
    if fail_start:
        stream.close.assert_called_once()
        assert not backend._input_active
        assert backend.stream is None


@pytest.mark.parametrize("backend_cls", [NativeBackend, PyaudioBackend, PygameBackend])
@pytest.mark.parametrize("duration_ms,accepted", [(0, False), (99, False), (100, True), (200, True)])
@pytest.mark.parametrize("chunk_size", [32, 65536])
def test_minimum_capture_duration_ignores_callback_chunk_size(backend_cls, duration_ms, accepted, chunk_size):
    backend = backend_cls(window=None)
    rate, channels = 16000, 2
    width = 4 if backend_cls is PygameBackend else 2
    backend.rate, backend.channels = rate, channels
    if backend_cls is NativeBackend:
        backend.actual_audio_format = SimpleNamespace(
            sampleRate=lambda: rate, channelCount=lambda: channels, bytesPerSample=lambda: width,
        )
    elif backend_cls is PyaudioBackend:
        backend._in_rate, backend._in_channels = rate, channels
        backend.pyaudio_instance = SimpleNamespace(get_sample_size=lambda fmt: width)
    pcm = bytes(rate * channels * width * duration_ms // 1000)
    backend.frames = [pcm[i:i + chunk_size] for i in range(0, len(pcm), chunk_size)]
    assert backend.has_min_frames() is accepted


def test_native_stop_saves_pending_partial_buffer(monkeypatch):
    from unittest.mock import MagicMock
    from PySide6.QtCore import QByteArray

    backend = NativeBackend(window=None)
    backend.audio_source = MagicMock()
    backend.audio_io_device = MagicMock()
    backend.audio_io_device.readAll.return_value = QByteArray(b"last samples")
    backend._is_recording = True
    monkeypatch.setattr(backend, "reset_audio_level", lambda: None)
    monkeypatch.setattr(backend, "_emit_rt_input_delta", lambda *args, **kwargs: None)
    saved = []
    monkeypatch.setattr(backend, "save_audio_file", lambda path: saved.append(b"".join(backend.frames)))

    assert backend.stop() is True
    assert saved == [b"last samples"]
