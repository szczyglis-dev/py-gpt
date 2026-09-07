from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.textarea.output import ChatOutput


def _window():
    return SimpleNamespace(
        core=SimpleNamespace(
            filesystem=SimpleNamespace(url=SimpleNamespace(handle=MagicMock())),
            config=SimpleNamespace(data={}, save=MagicMock()),
        ),
        controller=SimpleNamespace(
            chat=SimpleNamespace(common=SimpleNamespace(save_text=MagicMock())),
            audio=SimpleNamespace(read_text=MagicMock()),
            finder=SimpleNamespace(open=MagicMock(), focus_in=MagicMock()),
            settings=SimpleNamespace(editor=SimpleNamespace(get_option=MagicMock(return_value={}))),
            config=SimpleNamespace(apply=MagicMock()),
            ui=SimpleNamespace(update_font_size=MagicMock()),
        ),
    )


def test_set_tab_and_external_link_routing():
    window = _window()
    widget = SimpleNamespace(window=window, tab=None)
    tab = object()
    ChatOutput.set_tab(widget, tab)
    assert widget.tab is tab

    url = object()
    ChatOutput.open_external_link(widget, url)
    window.core.filesystem.url.handle.assert_called_once_with(url)


def test_save_selected_text_only_when_selection_exists():
    window = _window()
    selection = MagicMock()
    selection.toPlainText.return_value = "selected"
    cursor = MagicMock()
    cursor.hasSelection.return_value = True
    cursor.selection.return_value = selection
    widget = SimpleNamespace(window=window, textCursor=MagicMock(return_value=cursor))
    ChatOutput._save_selected_text(widget)
    window.controller.chat.common.save_text.assert_called_once_with("selected")

    window.controller.chat.common.save_text.reset_mock()
    cursor.hasSelection.return_value = False
    ChatOutput._save_selected_text(widget)
    window.controller.chat.common.save_text.assert_not_called()


def test_save_all_text_and_audio_selection_route_to_controllers():
    window = _window()
    cursor = MagicMock()
    cursor.selectedText.return_value = "say me"
    widget = SimpleNamespace(
        window=window,
        toPlainText=MagicMock(return_value="all text"),
        textCursor=MagicMock(return_value=cursor),
    )
    ChatOutput._save_all_text(widget)
    ChatOutput.audio_read_selection(widget)
    window.controller.chat.common.save_text.assert_called_once_with("all text")
    window.controller.audio.read_text.assert_called_once_with("say me")


def test_find_open_and_update_manage_finder():
    window = _window()
    finder = MagicMock()
    widget = SimpleNamespace(window=window, finder=finder)
    ChatOutput.find_open(widget)
    window.controller.finder.open.assert_called_once_with(finder)
    ChatOutput.on_update(widget)
    finder.clear.assert_called_once_with()


def test_zoom_change_updates_config_option_and_font_size():
    window = _window()
    option = {"value": 10}
    window.controller.settings.editor.get_option.return_value = option
    widget = SimpleNamespace(window=window, value=10)

    ChatOutput.on_zoom_changed(widget, 15)

    assert widget.value == 15
    assert window.core.config.data["font_size"] == 15
    window.core.config.save.assert_called_once_with()
    assert option["value"] == 15
    window.controller.config.apply.assert_called_once_with(
        parent_id="config", key="font_size", option=option
    )
    window.controller.ui.update_font_size.assert_called_once_with()


def test_auto_scroll_margin_uses_page_step_and_clamps():
    bar = MagicMock()
    widget = SimpleNamespace(verticalScrollBar=MagicMock(return_value=bar))

    bar.pageStep.return_value = 0
    assert ChatOutput._calc_auto_scroll_margin(widget) == 2
    bar.pageStep.return_value = 10
    assert ChatOutput._calc_auto_scroll_margin(widget) == 2
    bar.pageStep.return_value = 400
    assert ChatOutput._calc_auto_scroll_margin(widget) == 40
    bar.pageStep.return_value = 10000
    assert ChatOutput._calc_auto_scroll_margin(widget) == 64


def test_was_at_bottom_uses_dynamic_margin():
    bar = MagicMock()
    bar.maximum.return_value = 100
    bar.value.return_value = 95
    widget = SimpleNamespace(
        verticalScrollBar=MagicMock(return_value=bar),
        _calc_auto_scroll_margin=MagicMock(return_value=5),
    )
    assert ChatOutput.was_at_bottom(widget) is True
    bar.value.return_value = 94
    assert ChatOutput.was_at_bottom(widget) is False


def test_scroll_change_updates_auto_scroll_flag():
    widget = SimpleNamespace(_auto_scroll=False, was_at_bottom=MagicMock(return_value=True))
    ChatOutput._on_vsb_value_changed(widget, 50)
    assert widget._auto_scroll is True
    widget.was_at_bottom.return_value = False
    ChatOutput._on_vsb_value_changed(widget, 60)
    assert widget._auto_scroll is False


def test_auto_scroll_enabled_returns_internal_flag():
    assert ChatOutput.is_auto_scroll_enabled(SimpleNamespace(_auto_scroll=True)) is True
    assert ChatOutput.is_auto_scroll_enabled(SimpleNamespace(_auto_scroll=False)) is False
