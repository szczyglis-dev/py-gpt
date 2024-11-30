#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.30 04:00:00                  #
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
    assert "api_key" in data


def test_settings_section():
    config = Config()
    path = os.path.join(config.get_app_path(), "data", "config", "settings_section.json")
    with open(path, "r") as f:
        data = json.load(f)
    assert "general" in data


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
    files = [
        "style.css",
        "style.dark.css",
        "style.light.css",
        "markdown.css",
        "markdown.dark.css",
        "markdown.light.css",
        "fix_windows.css",
    ]
    for file in files:
        assert os.path.exists(os.path.join(path, file))


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
    files = [
        "locale.en.ini",
        "plugin.agent.en.ini",
        "plugin.audio_output.en.ini",
        "plugin.audio_input.en.ini",
        "plugin.cmd_api.en.ini",
        "plugin.cmd_code_interpreter.en.ini",
        "plugin.cmd_custom.en.ini",
        "plugin.cmd_files.en.ini",
        "plugin.cmd_serial.en.ini",
        "plugin.cmd_web.en.ini",
        "plugin.crontab.en.ini",
        "plugin.idx_llama_index.en.ini",
        "plugin.openai_dalle.en.ini",
        "plugin.openai_vision.en.ini",
        "plugin.real_time.en.ini",
    ]
    for file in files:
        assert os.path.exists(os.path.join(path, file))

    all_files = os.listdir(path)
    # check if .ini is parsing correctly
    for file in all_files:
        if file.endswith(".ini"):
            ini = configparser.ConfigParser()
            path = os.path.join(config.get_app_path(), "data", "locale", file)
            data = io.open(path, mode="r", encoding="utf-8")
            ini.read_string(data.read())
            assert len(ini) > 0