from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.layout.toolbox.indexes import Indexes


def _indexes():
    select = MagicMock()
    window = SimpleNamespace(
        ui=SimpleNamespace(nodes={"indexes.select": select}),
        controller=SimpleNamespace(settings=MagicMock()),
    )
    return SimpleNamespace(window=window, _last_combo_signature=None), select


def test_update_builds_placeholder_and_id_name_pairs():
    widget, select = _indexes()
    data = [
        {"id": "idx-1", "name": "Docs"},
        {"id": "idx-2", "name": ""},
    ]
    Indexes.update(widget, data)
    select.set_keys.assert_called_once_with([
        {"-": "---"},
        {"idx-1": "Docs"},
        {"idx-2": "idx-2"},
    ])
    assert widget._last_combo_signature == (("idx-1", "Docs"), ("idx-2", "idx-2"))


def test_update_skips_combo_refresh_when_signature_unchanged():
    widget, select = _indexes()
    data = [{"id": "idx", "name": "Docs"}]
    Indexes.update(widget, data)
    select.reset_mock()
    Indexes.update(widget, data)
    select.set_keys.assert_not_called()


def test_update_refreshes_when_display_name_changes():
    widget, select = _indexes()
    Indexes.update(widget, [{"id": "idx", "name": "Old"}])
    select.reset_mock()
    Indexes.update(widget, [{"id": "idx", "name": "New"}])
    select.set_keys.assert_called_once()


def test_open_llama_index_settings_delegates_to_settings_controller():
    widget, _ = _indexes()
    Indexes._open_llama_index_settings(widget)
    widget.window.controller.settings.open_section.assert_called_once_with("llama-index")
