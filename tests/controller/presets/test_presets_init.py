#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.presets import Presets
from pygpt_net.item.preset import PresetItem


def test_select(mock_window):
    """Test select preset"""
    presets = Presets(mock_window)
    presets.preset_change_locked = MagicMock(return_value=False)
    mock_window.core.config.data['mode'] = "chat"
    mock_window.core.presets.get_by_idx = MagicMock(return_value='preset_id')

    presets.select(1)
    mock_window.core.config.data['preset'] = "preset_id"
    mock_window.core.config.data['current_preset']["chat"] = "preset_id"


def test_use(mock_window):
    """Test use preset"""
    presets = Presets(mock_window)
    mock_window.controller.chat.render.append_to_input = MagicMock()
    mock_window.ui.nodes['preset.prompt'].toPlainText = MagicMock(return_value="preset_prompt")
    presets.use()
    mock_window.controller.chat.common.append_to_input.assert_called_once_with("preset_prompt")


def test_set(mock_window):
    """Test set preset"""
    presets = Presets(mock_window)
    mock_window.core.presets.has = MagicMock(return_value=True)
    presets.set("mode", "preset")
    mock_window.core.config.data['preset'] = "preset"
    mock_window.core.config.data['current_preset']["mode"] = "preset"


def test_set_by_idx(mock_window):
    """Test set preset by index"""
    presets = Presets(mock_window)
    mock_window.core.presets.get_by_idx = MagicMock(return_value='preset_id')
    presets.set_by_idx("mode", 1)
    mock_window.core.config.data['preset'] = "preset_id"
    mock_window.core.config.data['current_preset']["mode"] = "preset_id"


def test_select_current(mock_window):
    """Test select preset by current"""
    presets = Presets(mock_window)
    mock_window.core.config.get = MagicMock(side_effect=["chat", "preset_id"])
    mock_window.core.presets.get_by_mode = MagicMock(return_value={"preset_id": PresetItem()})
    mock_window.ui.models['preset.presets'].index = MagicMock(return_value="current")
    mock_window.ui.nodes['preset.presets'].setCurrentIndex = MagicMock()
    presets.select_current()
    mock_window.ui.nodes['preset.presets'].setCurrentIndex.assert_called_once_with("current")


def test_select_default(mock_window):
    """Test select default preset"""
    presets = Presets(mock_window)
    mock_window.core.config.data['current_preset'] = {}
    mock_window.core.config.get = MagicMock(side_effect=["chat", "preset_id"])
    mock_window.core.presets.get_default = MagicMock(return_value="preset_id")
    presets.select_default()
    mock_window.core.config.data['preset'] = "preset_id"
    mock_window.core.config.data['current_preset']["chat"] = "preset_id"


def test_update_data(mock_window):
    """Test update preset data"""
    presets = Presets(mock_window)
    mock_window.core.config.data["preset"] = "preset_id"
    mock_window.core.presets = MagicMock()

    preset = PresetItem()
    preset.ai_name = "preset_ai_name"
    preset.user_name = "preset_user_name"
    preset.prompt = "preset_prompt"
    mock_window.core.presets.items = {"preset_id": preset}

    mock_window.ui.nodes['preset.prompt'].setPlainText = MagicMock()
    mock_window.ui.nodes['preset.ai_name'].setText = MagicMock()
    mock_window.ui.nodes['preset.user_name'].setText = MagicMock()

    presets.update_data()
    mock_window.ui.nodes['preset.prompt'].setPlainText.assert_called_once_with("preset_prompt")
    # mock_window.ui.nodes['preset.ai_name'].setText.assert_called()


def test_update_current(mock_window):
    """Test update current preset"""
    presets = Presets(mock_window)
    mock_window.core.config.data["mode"] = "chat"
    mock_window.core.config.data["preset"] = "preset_id"

    preset = PresetItem()
    preset.ai_name = "preset_ai_name"
    preset.user_name = "preset_user_name"
    preset.prompt = "preset_prompt"
    preset.temperature = 0.5
    mock_window.core.presets.items = {"preset_id": preset}

    presets.update_current()
    assert mock_window.core.config.data["user_name"] == "preset_user_name"
    assert mock_window.core.config.data["ai_name"] == "preset_ai_name"
    assert mock_window.core.config.data["prompt"] == "preset_prompt"
    assert mock_window.core.config.data["temperature"] == 0.5


def test_refersh(mock_window):
    """Test refresh presets"""
    presets = Presets(mock_window)
    presets.select_default = MagicMock()
    presets.update_current = MagicMock()
    presets.update_data = MagicMock()
    mock_window.controller.mode.update_temperature = MagicMock()
    presets.update_list = MagicMock()
    presets.select_current = MagicMock()

    presets.refresh()
    presets.select_default.assert_called_once()
    presets.update_current.assert_called_once()
    presets.update_data.assert_called_once()
    mock_window.controller.mode.update_temperature.assert_called_once()
    presets.update_list.assert_called_once()
    presets.select_current.assert_called_once()


def test_update_list(mock_window):
    """Test update presets list"""
    presets = Presets(mock_window)
    mock_window.core.config.data["mode"] = "chat"

    preset = PresetItem()
    preset.ai_name = "preset_ai_name"
    preset.user_name = "preset_user_name"
    preset.prompt = "preset_prompt"
    preset.temperature = 0.5
    items = {"preset_id": preset}
    mock_window.core.presets.get_by_mode = MagicMock(return_value=items)

    mock_window.ui.toolbox.presets.update = MagicMock()
    presets.update_list()
    mock_window.ui.toolbox.presets.update.assert_called_once_with(items)


def test_reset(mock_window):
    """Test reset preset data"""
    presets = Presets(mock_window)
    mock_window.ui.nodes['preset.prompt'].setPlainText = MagicMock()
    mock_window.ui.nodes['preset.ai_name'].setText = MagicMock()
    mock_window.ui.nodes['preset.user_name'].setText = MagicMock()

    presets.reset()
    mock_window.ui.nodes['preset.prompt'].setPlainText.assert_called()
    # mock_window.ui.nodes['preset.ai_name'].setText.assert_called()
    # mock_window.ui.nodes['preset.user_name'].setText.assert_called()


def test_make_filename(mock_window):
    """Test make preset filename"""
    presets = Presets(mock_window)
    assert presets.make_filename("Test") == "test"
    assert presets.make_filename("Test 1") == "test_1"
    assert presets.make_filename("Test 1.2") == "test_1.2"
    assert presets.make_filename("Test 1.2.3") == "test_1.2.3"


def test_duplicate(mock_window):
    """Test duplicate preset"""
    presets = Presets(mock_window)
    presets.editor = MagicMock()
    presets.refresh = MagicMock()

    mock_window.core.config.data["mode"] = "chat"
    mock_window.core.config.data["preset"] = "preset_id"
    preset = PresetItem()
    preset.ai_name = "preset_ai_name"
    preset.user_name = "preset_user_name"
    preset.prompt = "preset_prompt"
    preset.temperature = 0.5

    mock_window.core.presets = MagicMock()
    mock_window.core.presets.items = {"preset_id": preset}
    mock_window.core.presets.get_by_idx = MagicMock(return_value="preset_id")
    mock_window.core.presets.duplicate = MagicMock(return_value="new_id")
    mock_window.core.presets.get_idx_by_id = MagicMock(return_value=3)
    mock_window.ui.status = MagicMock()
    mock_window.ui.nodes['presets'].edit = MagicMock()

    presets.duplicate(2)
    assert mock_window.core.config.data['preset'] == "new_id"
    presets.editor.edit.assert_called_once_with(3)
    presets.refresh.assert_called_once()


def test_clear(mock_window):
    """Test clear preset"""
    presets = Presets(mock_window)
    presets.refresh = MagicMock()
    mock_window.core.config.data["mode"] = "chat"
    mock_window.core.config.data["preset"] = "preset_id"

    preset = PresetItem()
    preset.ai_name = "preset_ai_name"
    preset.user_name = "preset_user_name"
    preset.prompt = "preset_prompt"
    preset.temperature = 0.5
    mock_window.core.presets.items = {"preset_id": preset}

    presets.clear(True)
    assert mock_window.core.config.data['ai_name'] == ""
    assert mock_window.core.config.data['user_name'] == ""
    assert mock_window.core.config.data['prompt'] == ""
    assert mock_window.core.config.data['temperature'] == 1.0

    assert preset.ai_name == ""
    assert preset.user_name == ""
    assert preset.prompt == ""
    assert preset.temperature == 1.0

    presets.refresh.assert_called_once()


def test_delete(mock_window):
    """Test delete preset"""
    presets = Presets(mock_window)
    presets.refresh = MagicMock()
    mock_window.core.config.data["mode"] = "chat"
    mock_window.core.config.data["preset"] = "preset_id"

    preset = PresetItem()
    preset.ai_name = "preset_ai_name"
    preset.user_name = "preset_user_name"
    preset.prompt = "preset_prompt"
    preset.temperature = 0.5
    mock_window.core.presets = MagicMock()
    mock_window.core.presets.items = {"preset_id": preset}
    mock_window.core.presets.get_by_idx = MagicMock(return_value="preset_id")

    presets.delete(2, force=True)
    assert mock_window.core.config.data['preset'] is None

    presets.refresh.assert_called_once()


def test_validate_filename(mock_window):
    """Test validate filename"""
    presets = Presets(mock_window)
    assert presets.validate_filename("Test") == "Test"
    assert presets.validate_filename("Test 1") == "Test 1"
    assert presets.validate_filename("Test 1.2") == "Test 1.2"
    assert presets.validate_filename("Test 1.2.3") == "Test 1.2.3"
    assert presets.validate_filename("Test/\\$1.2.3") == "Test1.2.3"


def test_preset_change_locked(mock_window):
    presets = Presets(mock_window)
    assert presets.preset_change_locked() is False
