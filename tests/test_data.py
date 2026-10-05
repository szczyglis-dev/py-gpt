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
import configparser
import io
import json
import os

from pygpt_net.config import Config


def test_config():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "config.json")
    with open(path, "r") as f:
        data = json.load(f)
    assert "__meta__" in data
    assert "api_custom_providers" in data
    assert data["api_custom_providers"] == []


def test_models():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "models.json")
    with open(path, "r") as f:
        data = json.load(f)
    assert "__meta__" in data


def test_modes():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "modes.json")
    with open(path, "r") as f:
        data = json.load(f)
    assert "__meta__" in data


def test_settings():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "settings.json")
    with open(path, "r") as f:
        data = json.load(f)
    # Provider API settings are declared dynamically by LLM providers and
    # are no longer stored as top-level entries in settings.json.
    assert "api_key" not in data
    assert "api_custom_providers" in data
    custom = data["api_custom_providers"]
    assert custom["section"] == "custom_providers"
    assert custom["type"] == "dict"
    assert custom["keys"]["api_key"]["secret"] is True


def test_settings_section():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "settings_section.json")
    with open(path, "r") as f:
        data = json.load(f)
    assert "general" in data
    assert data["custom_providers"]["label"] == "settings.section.custom_providers"


def test_presets():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "presets")
    for file in os.listdir(path):
        if file.endswith(".json"):
            with open(os.path.join(path, file), "r") as f:
                data = json.load(f)
            assert "__meta__" in data


def test_css():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "css")

    # Global CSS layers shared by all themes.
    files = [
        "app.css",
        "chat.css",
        "chat.wide.css",
        "fix_windows.css",
        "fix_windows.dark.css",
        "fix_windows.light.css",
        "agent_workflow.css",
    ]
    for file in files:
        assert os.path.exists(os.path.join(path, file))

    # Every bundled theme is now a directory containing its native Qt,
    # qt-material and WebEngine layers.
    themes = [
        "light",
        "mint",
        "gray",
        "dark",
        "matrix",
        "flare",
        "retro",
        "ocean",
        "sun",
    ]
    for theme in themes:
        theme_path = os.path.join(path, theme)
        for file in ("app.css", "app.xml", "chat.css"):
            assert os.path.exists(os.path.join(theme_path, file))


def test_fonts():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "fonts", "Lato")
    files = [
        "Lato-BlackItalic.ttf",
        "Lato-Black.ttf",
        "Lato-BoldItalic.ttf",
        "Lato-Bold.ttf",
        "Lato-Italic.ttf",
        "Lato-LightItalic.ttf",
        "Lato-Light.ttf",
        "Lato-Regular.ttf",
        "Lato-ThinItalic.ttf",
        "Lato-Thin.ttf",
    ]
    for file in files:
        assert os.path.exists(os.path.join(path, file))


def test_locale():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "locale")

    # Core application locales stay at data/locale/locale.<lang>.ini.
    assert os.path.exists(os.path.join(path, "locale.en.ini"))

    # Plugin locales are isolated in per-plugin locale domains.
    plugin_ids = [
        "agent",
        "audio_output",
        "audio_input",
        "cmd_api",
        "filesystem",
        "cmd_custom",
        "cmd_serial",
        "cmd_web",
        "crontab",
        "idx_llama_index",
        "openai_dalle",
        "openai_vision",
        "real_time",
    ]
    for plugin_id in plugin_ids:
        plugin_locale = os.path.join(path, "plugin", plugin_id, "locale.en.ini")
        assert os.path.exists(plugin_locale)

    # Every bundled INI, including nested plugin domains, must parse cleanly.
    for dirpath, _, filenames in os.walk(path):
        for file in filenames:
            if not file.endswith(".ini"):
                continue
            ini = configparser.ConfigParser()
            file_path = os.path.join(dirpath, file)
            with io.open(file_path, mode="r", encoding="utf-8") as data:
                ini.read_string(data.read())
            assert len(ini) > 0

            # These keys belong to the core locale domain only.
            if dirpath == path and file.startswith("locale."):
                locale = ini["LOCALE"]
                for key in (
                    "settings.section.custom_providers",
                    "settings.custom_providers.list",
                    "settings.custom_providers.list.desc",
                    "settings.custom_providers.name",
                    "settings.custom_providers.api_base",
                    "settings.custom_providers.api_key",
                ):
                    assert key in locale

