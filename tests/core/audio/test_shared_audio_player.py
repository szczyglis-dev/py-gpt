from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.audio.backend.shared.player as player_module
from pygpt_net.core.audio.backend.shared.player import NativePlayer


def test_shared_audio_player_stop_and_volume_use_safe_emit(monkeypatch):
    player = NativePlayer(window=None, chunk_ms=20)
    player.player = MagicMock()
    player.player.position.return_value = 25
    player.envelope = [10, 55]
    player.playback_timer = MagicMock()
    player.volume_timer = MagicMock()
    signals = object()
    emitted = []
    monkeypatch.setattr(player_module, "safe_emit", lambda source, name, *args: emitted.append((name, args)) or True)

    player.update_volume(signals)
    player.stop(signals)

    assert emitted[0] == ("volume_changed", (55,))
    assert emitted[-1] == ("volume_changed", (0,))
    player.player.stop.assert_called_once_with()
    assert player.playback_timer is None
    assert player.volume_timer is None


def test_shared_audio_player_update_volume_ignores_missing_player(monkeypatch):
    player = NativePlayer(window=None)
    emitted = []
    monkeypatch.setattr(player_module, "safe_emit", lambda *args: emitted.append(args) or True)

    player.update_volume(SimpleNamespace())

    assert emitted == []
