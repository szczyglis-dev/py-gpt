from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.audio.backend.native.player as player_module
from pygpt_net.core.audio.backend.native.player import NativePlayer


def make_player():
    player = NativePlayer(window=None, chunk_ms=10)
    player.playback_timer = MagicMock()
    player.volume_timer = MagicMock()
    return player


def test_native_audio_player_stop_timers_clears_both_timers():
    player = make_player()
    playback = player.playback_timer
    volume = player.volume_timer

    player.stop_timers()

    playback.stop.assert_called_once_with()
    volume.stop.assert_called_once_with()
    assert player.playback_timer is None
    assert player.volume_timer is None


def test_native_audio_player_stop_stops_media_and_resets_volume(monkeypatch):
    player = make_player()
    player.player = MagicMock()
    signals = object()
    emitted = []
    monkeypatch.setattr(player_module, "safe_emit", lambda source, name, *args: emitted.append((source, name, args)) or True)

    player.stop(signals)

    player.player.stop.assert_called_once_with()
    assert emitted == [(signals, "volume_changed", (0,))]
    assert player.playback_timer is None
    assert player.volume_timer is None


def test_native_audio_player_update_volume_uses_position_bucket(monkeypatch):
    player = NativePlayer(window=None, chunk_ms=10)
    player.player = SimpleNamespace(position=lambda: 25)
    player.envelope = [1, 2, 33]
    signals = object()
    emitted = []
    monkeypatch.setattr(player_module, "safe_emit", lambda source, name, *args: emitted.append((source, name, args)) or True)

    player.update_volume(signals)

    assert emitted == [(signals, "volume_changed", (33,))]


def test_native_audio_player_update_volume_falls_back_to_zero(monkeypatch):
    player = NativePlayer(window=None, chunk_ms=10)
    player.player = SimpleNamespace(position=lambda: 999)
    player.envelope = [1]
    emitted = []
    monkeypatch.setattr(player_module, "safe_emit", lambda source, name, *args: emitted.append(args) or True)

    player.update_volume(object())

    assert emitted == [(0,)]
