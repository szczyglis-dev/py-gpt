from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.chat.remote_tools import RemoteTools


def _window():
    window = MagicMock()
    window.core.config.get = MagicMock(return_value=False)
    window.core.config.set = MagicMock()
    window.core.config.save = MagicMock()
    window.core.models.get = MagicMock()
    window.ui.nodes = {"input": MagicMock()}
    return window


def test_remote_tools_setup_loads_global_state_and_updates_icon():
    window = _window()
    window.core.config.get.return_value = True
    remote = RemoteTools(window)
    remote.update_icons = MagicMock()

    remote.setup()

    window.core.config.get.assert_called_once_with("remote_tools.global.web_search", False)
    assert remote.enabled_global["web_search"] is True
    remote.update_icons.assert_called_once_with()


def test_remote_tools_enabled_resolves_model_name_and_handles_missing_model():
    window = _window()
    remote = RemoteTools(window)
    model = SimpleNamespace(provider="openai")
    window.core.models.get.return_value = model
    remote.is_web = MagicMock(return_value=True)

    assert remote.enabled("gpt", "web_search") is True
    window.core.models.get.assert_called_once_with("gpt")
    remote.is_web.assert_called_once_with(model)

    window.core.models.get.return_value = None
    assert remote.enabled("missing", "web_search") is False


def test_remote_tools_enabled_rejects_unknown_tool_name():
    remote = RemoteTools(_window())
    model = SimpleNamespace(provider="openai")

    assert remote.enabled(model, "unknown") is False


@pytest.mark.parametrize(
    "provider,key",
    [
        ("openai", "remote_tools.web_search"),
        ("google", "remote_tools.google.web_search"),
        ("anthropic", "remote_tools.anthropic.web_search"),
        ("x_ai", "remote_tools.xai.web_search"),
    ],
)
def test_remote_tools_is_web_uses_provider_specific_option(provider, key):
    window = _window()

    def cfg_get(name, default=False):
        return name == key

    window.core.config.get.side_effect = cfg_get
    remote = RemoteTools(window)
    remote.enabled_global["web_search"] = False

    assert remote.is_web(SimpleNamespace(provider=provider)) is True


def test_remote_tools_is_web_falls_back_to_global_state():
    window = _window()
    window.core.config.get.return_value = False
    remote = RemoteTools(window)
    remote.enabled_global["web_search"] = True

    assert remote.is_web(SimpleNamespace(provider="custom")) is True
    assert remote.is_web(SimpleNamespace(provider="openai")) is True


def test_remote_tools_update_icons_reflects_global_state():
    window = _window()
    remote = RemoteTools(window)

    remote.enabled_global["web_search"] = True
    remote.update_icons()
    window.ui.nodes["input"].set_icon_state.assert_called_with("web", True)

    remote.enabled_global["web_search"] = False
    remote.update_icons()
    window.ui.nodes["input"].set_icon_state.assert_called_with("web", False)


def test_remote_tools_toggle_web_search_updates_all_compatible_options():
    window = _window()
    remote = RemoteTools(window)
    remote.update_icons = MagicMock()

    remote.toggle("web_search")

    assert remote.enabled_global["web_search"] is True
    expected = {
        ("remote_tools.global.web_search", True),
        ("remote_tools.web_search", True),
        ("remote_tools.google.web_search", True),
        ("remote_tools.anthropic.web_search", True),
        ("remote_tools.xai.web_search", True),
    }
    assert {c.args for c in window.core.config.set.call_args_list} == expected
    window.core.config.save.assert_called_once_with()
    remote.update_icons.assert_called_once_with()


def test_remote_tools_toggle_unknown_tool_only_saves_and_refreshes_icons():
    window = _window()
    remote = RemoteTools(window)
    remote.update_icons = MagicMock()

    remote.toggle("unknown")

    window.core.config.set.assert_not_called()
    window.core.config.save.assert_called_once_with()
    remote.update_icons.assert_called_once_with()
