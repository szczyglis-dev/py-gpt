from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.settings import Settings


def test_extract_option_tabs_preserves_order_and_adds_general_for_untabbed_options():
    widget = SimpleNamespace()
    options = OrderedDict([
        ("a", {"tab": "advanced"}),
        ("b", {}),
        ("c", {"tab": "advanced"}),
        ("d", {"tab": "audio"}),
    ])
    assert Settings.extract_option_tabs(widget, options) == ["advanced", "audio", "general"]


def test_extract_option_tabs_defaults_to_general_when_empty():
    assert Settings.extract_option_tabs(SimpleNamespace(), {}) == ["general"]


def test_append_tabs_delegates_only_for_llama_index():
    append_tabs = MagicMock(return_value=["extra"])
    widget = SimpleNamespace(window=SimpleNamespace(controller=SimpleNamespace(idx=SimpleNamespace(settings=SimpleNamespace(append_tabs=append_tabs)))))
    assert Settings.append_tabs(widget, "llama-index") == ["extra"]
    assert Settings.append_tabs(widget, "general") == []
    append_tabs.assert_called_once_with()


def test_append_extra_delegates_for_llama_index():
    content = {"update": MagicMock()}
    idx_settings = MagicMock()
    widget = SimpleNamespace(
        add_line=MagicMock(return_value="line"),
        window=SimpleNamespace(controller=SimpleNamespace(idx=SimpleNamespace(settings=idx_settings))),
    )
    Settings.append_extra(widget, content, "llama-index", {"w": 1}, {"o": 2})
    content["update"].addWidget.assert_called_once_with("line")
    idx_settings.append.assert_called_once_with(content, {"w": 1}, {"o": 2})


def test_update_list_replaces_rows_and_translates_labels():
    model = MagicMock()
    model.rowCount.return_value = 3
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(models={"settings.section.list": model})))
    data = OrderedDict([
        ("general", {"label": "settings.general"}),
        ("audio", {"label": "settings.audio"}),
    ])
    with patch("pygpt_net.ui.dialog.settings.trans", side_effect=lambda key: f"T:{key}"):
        Settings.update_list(widget, "settings.section.list", data)
    model.removeRows.assert_called_once_with(0, 3)
    assert model.insertRow.call_count == 2
    assert [call.args[1] for call in model.setData.call_args_list] == ["T:settings.general", "T:settings.audio"]


def test_refresh_list_reads_sections_and_updates_section_list():
    sections = OrderedDict([
        ("general", {"label": "General"}),
        ("audio", {"label": "Audio"}),
    ])
    widget = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(settings=SimpleNamespace(get_sections=MagicMock(return_value=sections)))),
        update_list=MagicMock(),
    )
    Settings.refresh_list(widget)
    widget.update_list.assert_called_once_with("settings.section.list", dict(sections))
