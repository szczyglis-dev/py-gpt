from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.realtime.worker as realtime_module
from pygpt_net.core.events import RealtimeEvent
from pygpt_net.core.realtime.worker import RealtimeWorker


def make_window(client=None):
    if client is None:
        client = MagicMock()
    return SimpleNamespace(
        core=SimpleNamespace(
            api=SimpleNamespace(
                google=SimpleNamespace(realtime=SimpleNamespace(handler="google-client")),
                openai=SimpleNamespace(realtime=SimpleNamespace(handler=client)),
                xai=SimpleNamespace(realtime=SimpleNamespace(handler="xai-client")),
            ),
        ),
        controller=SimpleNamespace(kernel=SimpleNamespace(stopped=MagicMock(return_value=False))),
    )


def make_opts(signals, provider="openai"):
    return SimpleNamespace(
        rt_signals=signals,
        provider=provider,
        model="rt-model",
    )


def test_realtime_worker_selects_provider_clients_and_rejects_unknown():
    worker = RealtimeWorker(make_window(), object(), make_opts(object()))

    assert worker.get_client(None) is worker.window.core.api.openai.realtime.handler
    assert worker.get_client("OPENAI") is worker.window.core.api.openai.realtime.handler
    assert worker.get_client("google") == "google-client"
    assert worker.get_client("x_ai") == "xai-client"

    try:
        worker.get_client("other")
    except RuntimeError as exc:
        assert "Unsupported realtime provider" in str(exc)
    else:
        raise AssertionError("Unsupported provider must raise")


def test_realtime_worker_run_emits_ready_text_and_audio_events(monkeypatch):
    class Client:
        async def run(self, ctx, opts, on_text, on_audio, should_stop):
            assert should_stop() is False
            await on_text("")
            await on_text("hello")
            await on_audio(b"abc", "audio/pcm;rate=24000", 24000, 2, True)

    signals = object()
    ctx = object()
    worker = RealtimeWorker(make_window(Client()), ctx, make_opts(signals))
    emitted = []
    monkeypatch.setattr(realtime_module, "safe_emit", lambda source, name, event: emitted.append((source, name, event)) or True)

    worker.run()

    assert [entry[2].name for entry in emitted] == [
        RealtimeEvent.RT_OUTPUT_READY,
        RealtimeEvent.RT_OUTPUT_TEXT_DELTA,
        RealtimeEvent.RT_OUTPUT_AUDIO_DELTA,
    ]
    assert emitted[1][2].data == {"ctx": ctx, "chunk": "hello"}
    payload = emitted[2][2].data["payload"]
    assert payload["ctx"] is ctx
    assert payload["data"] == b"abc"
    assert payload["rate"] == 24000
    assert payload["channels"] == 2
    assert payload["final"] is True
    assert payload["provider"] == "openai"
    assert payload["model"] == "rt-model"


def test_realtime_worker_run_emits_audio_error(monkeypatch):
    class Client:
        async def run(self, *args, **kwargs):
            raise RuntimeError("socket failed")

    signals = object()
    worker = RealtimeWorker(make_window(Client()), object(), make_opts(signals))
    emitted = []
    monkeypatch.setattr(realtime_module, "safe_emit", lambda source, name, event: emitted.append(event) or True)

    worker.run()

    assert emitted[0].name == RealtimeEvent.RT_OUTPUT_READY
    assert emitted[-1].name == RealtimeEvent.RT_OUTPUT_AUDIO_ERROR
    assert isinstance(emitted[-1].data["error"], RuntimeError)
