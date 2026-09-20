from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.textarea.input import ChatInput


def _debug_window():
    return SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())))


def _input(**overrides):
    values = dict(
        _paste_max_chars=1000,
        window=_debug_window(),
    )
    values.update(overrides)
    obj = SimpleNamespace(**values)
    obj._sanitize_text = lambda text: ChatInput._sanitize_text(obj, text)
    return obj


@pytest.mark.parametrize(
    "value, expected",
    [
        ("a\r\nb\rc", "a\nb\nc"),
        ("a\x00b\x7fc", "abc"),
        ("a\x01b\tc\nd", "a b\tc\nd"),
        ("a\u200bb\u202ec\u2066d", "abcd"),
        (123, "123"),
        ("", ""),
        (None, ""),
    ],
)
def test_sanitize_text_normalizes_controls(value, expected):
    assert ChatInput._sanitize_text(_input(), value) == expected


def test_sanitize_text_honors_hard_cap_and_logs_truncation():
    widget = _input(_paste_max_chars=4)
    assert ChatInput._sanitize_text(widget, "abcdef") == "abcd"
    widget.window.core.debug.log.assert_called_once()


def test_sanitize_text_falls_back_to_default_limit_when_limit_is_invalid():
    widget = _input(_paste_max_chars="bad")
    text = "x" * 250001
    out = ChatInput._sanitize_text(widget, text)
    assert len(out) == 250000


@pytest.mark.parametrize("text, urls, image, expected", [
    (True, False, False, True),
    (False, True, False, True),
    (False, False, True, True),
    (False, False, False, False),
])
def test_can_insert_from_mime_data_allows_only_supported_payloads(text, urls, image, expected):
    source = MagicMock()
    source.hasText.return_value = text
    source.hasUrls.return_value = urls
    source.hasImage.return_value = image
    assert ChatInput.canInsertFromMimeData(SimpleNamespace(), source) is expected


def test_can_insert_from_mime_data_rejects_none_and_broken_source():
    assert ChatInput.canInsertFromMimeData(SimpleNamespace(), None) is False
    source = MagicMock()
    source.hasText.side_effect = RuntimeError("broken")
    assert ChatInput.canInsertFromMimeData(SimpleNamespace(), source) is False


def test_mime_has_local_file_urls_detects_any_local_url():
    remote = SimpleNamespace(isLocalFile=lambda: False)
    local = SimpleNamespace(isLocalFile=lambda: True)
    source = MagicMock()
    source.hasUrls.return_value = True
    source.urls.return_value = [remote, local]
    assert ChatInput._mime_has_local_file_urls(SimpleNamespace(), source) is True

    source.urls.return_value = [remote]
    assert ChatInput._mime_has_local_file_urls(SimpleNamespace(), source) is False


def test_safe_text_from_mime_prefers_text_over_urls():
    source = MagicMock()
    source.hasText.return_value = True
    source.text.return_value = " hello\r\nworld "
    widget = _input()
    assert ChatInput._safe_text_from_mime(widget, source) == " hello\nworld "
    source.hasUrls.assert_not_called()


def test_safe_text_from_mime_joins_only_remote_urls():
    local = SimpleNamespace(isLocalFile=lambda: True, toString=lambda: "file:///tmp/a")
    remote = SimpleNamespace(isLocalFile=lambda: False, toString=lambda: "https://example.com")
    source = MagicMock()
    source.hasText.return_value = False
    source.hasUrls.return_value = True
    source.urls.return_value = [local, remote]
    widget = _input()
    assert ChatInput._safe_text_from_mime(widget, source) == "https://example.com"


def test_safe_text_from_mime_logs_failure_and_returns_empty():
    source = MagicMock()
    source.hasText.side_effect = RuntimeError("bad mime")
    widget = _input()
    assert ChatInput._safe_text_from_mime(widget, source) == ""
    widget.window.core.debug.log.assert_called_once()


def test_set_text_top_padding_clamps_negative_and_reapplies_margins():
    widget = SimpleNamespace(_text_top_padding=5, _apply_margins=MagicMock())
    ChatInput.set_text_top_padding(widget, -10)
    assert widget._text_top_padding == 0
    widget._apply_margins.assert_called_once_with()

    ChatInput.set_text_top_padding(widget, "12")
    assert widget._text_top_padding == 12


def _icons_widget():
    left_a, left_b, right = MagicMock(), MagicMock(), MagicMock()
    return SimpleNamespace(
        _icons={"a": left_a, "b": left_b},
        _icons_right={"r": right},
        _icon_meta={"a": {"active": False}, "b": {"active": True}},
        _icon_meta_right={"r": {"active": False}},
        _icon_order=["a", "b"],
        _icon_order_right=["r"],
        _apply_icon_visual=MagicMock(),
        _rebuild_icon_layout=MagicMock(),
        _rebuild_icon_layout_right=MagicMock(),
        _update_icon_bar_geometry=MagicMock(),
        _update_icon_bar_geometry_right=MagicMock(),
        _apply_margins=MagicMock(),
    )


def test_icon_visibility_searches_both_bars():
    widget = _icons_widget()
    widget._icons["a"].isHidden.return_value = False
    widget._icons_right["r"].isHidden.return_value = True
    assert ChatInput.is_icon_visible(widget, "a") is True
    assert ChatInput.is_icon_visible(widget, "r") is False
    assert ChatInput.is_icon_visible(widget, "missing") is False


def test_icon_order_keeps_unlisted_existing_icons_at_end():
    widget = _icons_widget()
    ChatInput.set_icon_order(widget, ["b", "missing", "b"])
    assert widget._icon_order == ["b", "a"]
    widget._rebuild_icon_layout.assert_called_once_with()
    widget._update_icon_bar_geometry.assert_called_once_with()
    widget._apply_margins.assert_called_once_with()


def test_right_icon_order_filters_duplicates_and_unknown_keys():
    widget = _icons_widget()
    widget._icons_right["s"] = MagicMock()
    widget._icon_order_right = ["r", "s"]
    ChatInput.set_right_icon_order(widget, ["s", "unknown", "s"])
    assert widget._icon_order_right == ["s", "r"]
    widget._rebuild_icon_layout_right.assert_called_once_with()


def test_icon_state_accessors_and_toggle_cover_both_bars():
    widget = _icons_widget()
    widget.set_icon_state = MagicMock(side_effect=lambda key, state: ChatInput.set_icon_state(widget, key, state))

    assert ChatInput.get_icon_state(widget, "a") is False
    assert ChatInput.toggle_icon_state(widget, "a") is True
    assert widget._icon_meta["a"]["active"] is True
    assert ChatInput.toggle_icon_state(widget, "r") is True
    assert widget._icon_meta_right["r"]["active"] is True
    assert ChatInput.toggle_icon_state(widget, "missing") is False


def test_set_icon_tooltip_updates_base_or_alt_metadata():
    widget = _icons_widget()
    ChatInput.set_icon_tooltip(widget, "a", "base")
    ChatInput.set_icon_tooltip(widget, "a", "alt", for_alt=True)
    assert widget._icon_meta["a"]["tooltip"] == "base"
    assert widget._icon_meta["a"]["alt_tooltip"] == "alt"
    assert widget._apply_icon_visual.call_count == 2


def test_set_icon_callback_replaces_existing_connections():
    widget = _icons_widget()
    callback = MagicMock()
    ChatInput.set_icon_callback(widget, "a", callback)
    button = widget._icons["a"]
    button.clicked.disconnect.assert_called_once_with()
    button.clicked.connect.assert_called_once_with(callback)


def test_get_icon_button_prefers_left_then_right():
    widget = _icons_widget()
    assert ChatInput.get_icon_button(widget, "a") is widget._icons["a"]
    assert ChatInput.get_icon_button(widget, "r") is widget._icons_right["r"]
    assert ChatInput.get_icon_button(widget, "missing") is None


def test_effective_lines_handles_margin_and_invalid_line_height():
    widget = SimpleNamespace()
    assert ChatInput._effective_lines(widget, 100, 20, 10) == 4.0
    assert ChatInput._effective_lines(widget, 5, 20, 10) == 1.0
    assert ChatInput._effective_lines(widget, 100, 0, 10) == 1.0


def test_should_shrink_to_min_uses_line_spacing_and_document_margin():
    document = SimpleNamespace(documentMargin=lambda: 4.0)
    widget = SimpleNamespace(_line_spacing=lambda: 16, document=lambda: document)
    assert ChatInput._should_shrink_to_min(widget, 28) is True
    assert ChatInput._should_shrink_to_min(widget, 29) is False


def _history_widget(history=None, current="draft", limit=30):
    obj = SimpleNamespace(
        _history=list(history or []),
        _history_limit=limit,
        _history_index=-1,
        _history_active=False,
        _history_saved_current="",
        toPlainText=MagicMock(return_value=current),
        _set_text_and_move_end=MagicMock(),
    )
    obj._history_begin = lambda: ChatInput._history_begin(obj)
    obj._history_end = lambda restore_saved=True: ChatInput._history_end(obj, restore_saved)
    obj._normalize_history_text = lambda text: ChatInput._normalize_history_text(obj, text)
    obj.history_push = lambda text: ChatInput.history_push(obj, text)
    return obj


def test_history_begin_snapshots_current_text_once():
    widget = _history_widget(["one", "two"], current="draft")
    ChatInput._history_begin(widget)
    assert widget._history_active is True
    assert widget._history_saved_current == "draft"
    assert widget._history_index == 2

    widget.toPlainText.return_value = "changed"
    ChatInput._history_begin(widget)
    assert widget._history_saved_current == "draft"


def test_history_navigation_moves_older_then_restores_draft_past_newest():
    widget = _history_widget(["one", "two"], current="draft")
    ChatInput._history_navigate(widget, -1)
    assert widget._history_index == 1
    widget._set_text_and_move_end.assert_called_with("two")

    ChatInput._history_navigate(widget, -1)
    assert widget._history_index == 0
    widget._set_text_and_move_end.assert_called_with("one")

    ChatInput._history_navigate(widget, 1)
    assert widget._history_index == 1
    widget._set_text_and_move_end.assert_called_with("two")

    ChatInput._history_navigate(widget, 1)
    assert widget._history_active is False
    assert widget._history_index == -1
    widget._set_text_and_move_end.assert_called_with("draft")


def test_history_push_trims_deduplicates_and_ignores_empty():
    widget = _history_widget(["one"], limit=3)
    ChatInput.history_push(widget, " one ")
    ChatInput.history_push(widget, "")
    ChatInput.history_push(widget, "two")
    ChatInput.history_push(widget, "three")
    ChatInput.history_push(widget, "four")
    assert widget._history == ["two", "three", "four"]


def test_history_clear_resets_all_navigation_state():
    widget = _history_widget(["one", "two"])
    widget._history_index = 1
    widget._history_active = True
    widget._history_saved_current = "draft"
    ChatInput.history_clear(widget)
    assert widget._history == []
    assert widget._history_index == -1
    assert widget._history_active is False
    assert widget._history_saved_current == ""


def test_effectively_empty_strips_whitespace_and_fails_safe():
    widget = SimpleNamespace(toPlainText=MagicMock(return_value="  \n\t"))
    assert ChatInput._is_effectively_empty(widget) is True
    widget.toPlainText.return_value = "x"
    assert ChatInput._is_effectively_empty(widget) is False
    widget.toPlainText.side_effect = RuntimeError("gone")
    assert ChatInput._is_effectively_empty(widget) is True
