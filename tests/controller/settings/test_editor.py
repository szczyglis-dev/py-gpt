#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 12:30:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.settings.editor import Editor


def test_refresh_llm_provider_choices_updates_model_and_importer_widgets(monkeypatch):
    provider_keys = [
        {"openai": "OpenAI"},
        {"custom_my_api_12345678": "My API"},
    ]
    model_provider = MagicMock()
    model_provider_global = MagicMock()
    importer_provider = MagicMock()

    placeholder = MagicMock()
    placeholder.apply_by_id.return_value = provider_keys
    importer = MagicMock()
    importer.get_providers_option.return_value = {
        "keys": [{"_": "Select"}] + provider_keys
    }

    ui = SimpleNamespace(
        config={
            "model": {
                "provider": model_provider,
                "provider_global": model_provider_global,
            },
            "models.importer": {
                "provider": importer_provider,
            },
        }
    )
    window = SimpleNamespace(
        ui=ui,
        controller=SimpleNamespace(
            config=SimpleNamespace(placeholder=placeholder),
            model=SimpleNamespace(importer=importer),
        ),
    )
    monkeypatch.setattr(
        "pygpt_net.controller.settings.editor.trans",
        lambda key: "All" if key == "list.all" else key,
    )

    Editor(window).refresh_llm_provider_choices()

    model_provider.set_keys.assert_called_once_with(provider_keys)
    model_provider_global.set_keys.assert_called_once_with(
        [{"-": "All"}] + provider_keys
    )
    importer_provider.set_keys.assert_called_once_with(
        [{"_": "Select"}] + provider_keys
    )
