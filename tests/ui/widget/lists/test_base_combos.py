from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QComboBox

from pygpt_net.ui.widget.lists.base_combo import BaseCombo
from pygpt_net.ui.widget.lists.base_list_combo import BaseListCombo
from pygpt_net.ui.widget.lists.mode_combo import ModeCombo
from pygpt_net.ui.widget.lists.model_combo import ModelCombo
from pygpt_net.ui.widget.lists.llama_mode_combo import LlamaModeCombo


def test_base_combo_has_key_supports_plain_and_mapping_entries():
    widget = SimpleNamespace(keys=["plain", {"mapped": "Mapped"}])
    assert BaseCombo.has_key(widget, "plain") is True
    assert BaseCombo.has_key(widget, "mapped") is True
    assert BaseCombo.has_key(widget, "missing") is False


def test_base_combo_set_value_only_changes_known_value():
    combo = MagicMock()
    combo.findData.side_effect = [2, -1]
    widget = SimpleNamespace(combo=combo)

    BaseCombo.set_value(widget, "known")
    BaseCombo.set_value(widget, "missing")

    combo.setCurrentIndex.assert_called_once_with(2)


def test_base_combo_change_ignored_before_initialization():
    combo = MagicMock()
    widget = SimpleNamespace(initialized=False, combo=combo, current_id="old")

    BaseCombo.on_combo_change(widget, 3)

    assert widget.current_id == "old"
    combo.itemData.assert_not_called()


def test_base_combo_change_sets_current_id_after_initialization():
    combo = MagicMock()
    combo.itemData.return_value = "new"
    widget = SimpleNamespace(initialized=True, combo=combo, current_id=None)

    BaseCombo.on_combo_change(widget, 3)

    assert widget.current_id == "new"


def test_base_list_combo_has_key_excludes_sections_and_separators_and_caches():
    keys = ["one", {"two": "Two"}, {"section::x": "X"}, "separator::line"]
    widget = SimpleNamespace(keys=keys, _keys_cache=None, _keys_cache_id=0)

    assert BaseListCombo.has_key(widget, "one") is True
    assert BaseListCombo.has_key(widget, "two") is True
    assert BaseListCombo.has_key(widget, "section::x") is False
    cache = widget._keys_cache
    assert BaseListCombo.has_key(widget, "missing") is False
    assert widget._keys_cache is cache


def test_base_list_combo_set_value_uses_index_map_without_find():
    combo = MagicMock()
    combo.currentIndex.return_value = 0
    widget = SimpleNamespace(combo=combo, _data_index_map={"target": 4}, current_id=None, locked=False)

    with patch("pygpt_net.ui.widget.lists.base_list_combo.QSignalBlocker"):
        BaseListCombo.set_value(widget, "target")

    combo.findData.assert_not_called()
    combo.setCurrentIndex.assert_called_once_with(4)
    assert widget.current_id == "target"
    assert widget.locked is False


def test_base_list_combo_change_handles_negative_and_lock():
    combo = MagicMock()
    combo.itemData.return_value = "value"
    widget = SimpleNamespace(initialized=True, locked=True, combo=combo, current_id="old")
    BaseListCombo.on_combo_change(widget, 1)
    assert widget.current_id == "old"

    widget.locked = False
    BaseListCombo.on_combo_change(widget, -1)
    assert widget.current_id is None
    combo.itemData.assert_not_called()


def test_fit_to_content_uses_adjust_policy():
    combo = MagicMock()
    BaseCombo.fit_to_content(SimpleNamespace(combo=combo))
    combo.setSizeAdjustPolicy.assert_called_once_with(QComboBox.AdjustToContents)


def test_specialized_combo_callbacks_delegate_to_controllers():
    window = MagicMock()

    mode_combo = SimpleNamespace(initialized=True, locked=False, current_id=None, combo=MagicMock(), window=window)
    mode_combo.combo.itemData.return_value = "chat"
    model_combo = SimpleNamespace(initialized=True, locked=False, current_id=None, combo=MagicMock(), window=window)
    model_combo.combo.itemData.return_value = "gpt"
    llama_combo = SimpleNamespace(initialized=True, current_id=None, combo=MagicMock(), window=window)
    llama_combo.combo.itemData.return_value = "query"

    ModeCombo.on_combo_change(mode_combo, 2)
    ModelCombo.on_combo_change(model_combo, 3)
    LlamaModeCombo.on_combo_change(llama_combo, 4)

    window.controller.mode.select.assert_called_once_with("chat")
    window.controller.model.select.assert_called_once_with("gpt")
    window.controller.idx.select_mode.assert_called_once_with("query")
