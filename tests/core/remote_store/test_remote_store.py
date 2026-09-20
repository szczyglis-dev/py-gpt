from unittest.mock import MagicMock

import pygpt_net.core.remote_store.remote_store as store_module
from pygpt_net.core.remote_store.remote_store import RemoteStore


def test_remote_store_builds_provider_stores_with_same_window(monkeypatch):
    window = object()
    openai = MagicMock(return_value="openai")
    google = MagicMock(return_value="google")
    anthropic = MagicMock(return_value="anthropic")
    xai = MagicMock(return_value="xai")
    monkeypatch.setattr(store_module, "OpenAIStore", openai)
    monkeypatch.setattr(store_module, "GoogleStore", google)
    monkeypatch.setattr(store_module, "AnthropicStore", anthropic)
    monkeypatch.setattr(store_module, "XAIStore", xai)

    store = RemoteStore(window)

    assert (store.openai, store.google, store.anthropic, store.xai) == ("openai", "google", "anthropic", "xai")
    for mock in (openai, google, anthropic, xai):
        mock.assert_called_once_with(window)
