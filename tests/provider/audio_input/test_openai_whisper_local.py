#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.02 18:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.core.types import WHISPER_LOCAL_MODELS
from pygpt_net.provider.audio_input.openai_whisper_local import OpenAIWhisperLocal


def make_provider(options=None):
    """Create provider with a lightweight plugin mock."""
    options = options or {}
    plugin = MagicMock()
    plugin.get_option_value.side_effect = lambda key: options.get(key)
    plugin.window.core.config.is_compiled.return_value = False
    plugin.window.core.platforms.is_snap.return_value = False
    return OpenAIWhisperLocal(plugin=plugin), plugin


def test_whisper_local_model_list():
    """Keep the supported model list explicit and easy to extend."""
    assert len(WHISPER_LOCAL_MODELS) == 14
    assert WHISPER_LOCAL_MODELS["base"].startswith("base (")
    assert "large-v3" in WHISPER_LOCAL_MODELS
    assert "large-v3-turbo" in WHISPER_LOCAL_MODELS
    assert "turbo" in WHISPER_LOCAL_MODELS


def test_init_options_adds_model_combo_custom_override_and_memory_toggle():
    """Provider exposes combo, custom override and RAM retention settings."""
    provider, plugin = make_provider()

    provider.init_options()

    calls = {call.args[0]: call for call in plugin.add_option.call_args_list}
    model = calls["whisper_local_model"]
    custom = calls["whisper_local_model_custom"]
    keep = calls["whisper_local_keep_in_memory"]

    assert model.kwargs["type"] == "combo"
    assert model.kwargs["value"] == "base"
    assert model.kwargs["keys"] == WHISPER_LOCAL_MODELS
    assert custom.kwargs["type"] == "text"
    assert custom.kwargs["value"] == ""
    assert keep.kwargs["type"] == "bool"
    assert keep.kwargs["value"] is True


def test_get_model_name_uses_combo_value():
    provider, _ = make_provider({
        "whisper_local_model": "small",
        "whisper_local_model_custom": "",
    })

    assert provider.get_model_name() == "small"


def test_get_model_name_custom_override_has_priority():
    provider, _ = make_provider({
        "whisper_local_model": "base",
        "whisper_local_model_custom": "  future-model  ",
    })

    assert provider.get_model_name() == "future-model"


def test_get_model_name_falls_back_to_base():
    provider, _ = make_provider({
        "whisper_local_model": "",
        "whisper_local_model_custom": "",
    })

    assert provider.get_model_name() == "base"


def test_should_keep_model_in_memory_defaults_true():
    provider, _ = make_provider({"whisper_local_keep_in_memory": None})

    assert provider.should_keep_model_in_memory() is True


def test_should_keep_model_in_memory_can_be_disabled():
    provider, _ = make_provider({"whisper_local_keep_in_memory": False})

    assert provider.should_keep_model_in_memory() is False


def test_is_model_downloaded_accepts_custom_local_checkpoint(tmp_path):
    checkpoint = tmp_path / "custom.pt"
    checkpoint.write_bytes(b"model")
    provider, _ = make_provider({
        "whisper_local_model": "base",
        "whisper_local_model_custom": str(checkpoint),
    })

    assert provider.get_model_cache_path() == str(checkpoint)
    assert provider.is_model_downloaded() is True


def test_load_model_reuses_matching_model():
    provider, _ = make_provider({
        "whisper_local_model": "base",
        "whisper_local_model_custom": "",
    })
    whisper = MagicMock()
    model = MagicMock()
    whisper.load_model.return_value = model
    provider._import_whisper = MagicMock(return_value=whisper)
    provider._get_rss_bytes = MagicMock(return_value=100)
    provider._track_resident_growth = MagicMock()

    assert provider.load_model() is model
    assert provider.load_model() is model

    whisper.load_model.assert_called_once_with("base")
    provider._track_resident_growth.assert_called_once_with(100)
    assert provider.loaded_model_name == "base"


def test_load_model_releases_old_model_after_model_change():
    provider, _ = make_provider()
    provider.model = MagicMock()
    provider.loaded_model_name = "base"
    provider.release_model = MagicMock(side_effect=lambda: (
        setattr(provider, "model", None),
        setattr(provider, "loaded_model_name", None),
    ))
    whisper = MagicMock()
    new_model = MagicMock()
    whisper.load_model.return_value = new_model
    provider._import_whisper = MagicMock(return_value=whisper)
    provider._get_rss_bytes = MagicMock(return_value=100)
    provider._track_resident_growth = MagicMock()

    assert provider.load_model("small") is new_model

    provider.release_model.assert_called_once()
    whisper.load_model.assert_called_once_with("small")
    assert provider.loaded_model_name == "small"


def test_transcribe_keeps_model_when_enabled():
    provider, _ = make_provider()
    provider.is_configured = MagicMock(return_value=True)
    model = MagicMock()
    model.transcribe.return_value = {"text": "hello"}
    provider.load_model = MagicMock(return_value=model)
    provider.should_keep_model_in_memory = MagicMock(return_value=True)
    provider.release_model = MagicMock()
    provider._get_rss_bytes = MagicMock(return_value=100)
    provider._track_resident_growth = MagicMock()

    assert provider.transcribe("audio.wav") == "hello"

    provider.release_model.assert_not_called()


def test_transcribe_releases_model_when_disabled():
    provider, _ = make_provider()
    provider.is_configured = MagicMock(return_value=True)
    model = MagicMock()
    model.transcribe.return_value = {"text": "hello"}
    provider.load_model = MagicMock(return_value=model)
    provider.should_keep_model_in_memory = MagicMock(return_value=False)
    provider.release_model = MagicMock()
    provider._get_rss_bytes = MagicMock(return_value=100)
    provider._track_resident_growth = MagicMock()

    assert provider.transcribe("audio.wav") == "hello"

    provider.release_model.assert_called_once()


def test_apply_memory_policy_releases_when_keep_disabled():
    provider, _ = make_provider()
    provider.model = MagicMock()
    provider.loaded_model_name = "base"
    provider.should_keep_model_in_memory = MagicMock(return_value=False)
    provider.release_model = MagicMock()

    provider.apply_memory_policy()

    provider.release_model.assert_called_once()


def test_apply_memory_policy_releases_after_model_change():
    provider, _ = make_provider()
    provider.model = MagicMock()
    provider.loaded_model_name = "base"
    provider.should_keep_model_in_memory = MagicMock(return_value=True)
    provider.get_model_name = MagicMock(return_value="small")
    provider.release_model = MagicMock()

    provider.apply_memory_policy()

    provider.release_model.assert_called_once()


def test_get_memory_excluded_bytes_is_capped_to_process_rss():
    provider, _ = make_provider()
    provider._import_memory_bytes = 600
    provider._resident_memory_bytes = 700
    provider._get_rss_bytes = MagicMock(return_value=1000)

    assert provider.get_memory_excluded_bytes() == 1000


def test_compiled_whisper_accepts_available_runtime_packages():
    provider, plugin = make_provider()
    plugin.window.core.config.is_compiled.return_value = True
    plugin.window.core.platforms.is_snap.return_value = True
    provider._import_whisper = MagicMock()
    assert provider.is_configured() is True
