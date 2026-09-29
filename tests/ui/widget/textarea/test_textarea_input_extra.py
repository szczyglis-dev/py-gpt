from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.textarea.input_extra import ExtraInput


def _widget(**overrides):
    values = dict(
        _paste_max_chars=1000,
        window=SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock()))),
    )
    values.update(overrides)
    obj = SimpleNamespace(**values)
    obj._sanitize_text = lambda text: ExtraInput._sanitize_text(obj, text)
    return obj


def test_extra_input_sanitize_text_normalizes_controls_and_bidi_chars():
    widget = _widget()
    assert ExtraInput._sanitize_text(widget, "a\r\nb\x00\x01c\u200bd") == "a\nb cd"


def test_extra_input_sanitize_text_caps_large_paste():
    widget = _widget(_paste_max_chars=3)
    assert ExtraInput._sanitize_text(widget, "abcdef") == "abc"
    widget.window.core.debug.log.assert_called_once()


def test_extra_input_safe_text_prefers_plain_text():
    source = MagicMock()
    source.hasText.return_value = True
    source.text.return_value = "a\r\nb"
    widget = _widget()
    assert ExtraInput._safe_text_from_mime(widget, source) == "a\nb"


def test_extra_input_safe_text_skips_local_urls():
    source = MagicMock()
    source.hasText.return_value = False
    source.hasUrls.return_value = True
    source.urls.return_value = [
        SimpleNamespace(isLocalFile=lambda: True, toString=lambda: "file:///tmp/a"),
        SimpleNamespace(isLocalFile=lambda: False, toString=lambda: "https://example.com"),
    ]
    widget = _widget()
    assert ExtraInput._safe_text_from_mime(widget, source) == "https://example.com"


def test_get_main_splitter_returns_registered_splitter_or_none():
    splitter = object()
    widget = SimpleNamespace(window=SimpleNamespace(ui=SimpleNamespace(splitters={"main.output": splitter})))
    assert ExtraInput._get_main_splitter(widget) is splitter

    widget.window.ui = None
    assert ExtraInput._get_main_splitter(widget) is None


def test_find_container_in_splitter_returns_ancestor_and_index():
    first = MagicMock()
    second = MagicMock()
    first.isAncestorOf.return_value = False
    second.isAncestorOf.return_value = True
    splitter = MagicMock()
    splitter.count.return_value = 2
    splitter.widget.side_effect = [first, second]
    widget = SimpleNamespace()
    assert ExtraInput._find_container_in_splitter(widget, splitter) == (second, 1)
    assert ExtraInput._find_container_in_splitter(widget, None) == (None, -1)


def test_schedule_auto_resize_coalesces_flags_and_starts_timer_once():
    timer = MagicMock()
    timer.isActive.return_value = False
    widget = SimpleNamespace(
        _pending_force=False,
        _pending_minimize_if_single=False,
        _user_adjusting_splitter=False,
        _splitter_resize_in_progress=False,
        _auto_timer=timer,
        _auto_debounce_ms=0,
        _ensure_splitter_hook=MagicMock(),
    )
    ExtraInput._schedule_auto_resize(widget, force=True, enforce_minimize_if_single=False)
    assert widget._pending_force is True
    assert widget._pending_minimize_if_single is False
    widget._ensure_splitter_hook.assert_called_once_with()
    timer.start.assert_called_once_with(0)

    timer.isActive.return_value = True
    ExtraInput._schedule_auto_resize(widget, force=False, enforce_minimize_if_single=True)
    assert widget._pending_force is True
    assert widget._pending_minimize_if_single is True
    assert timer.start.call_count == 1


def test_schedule_auto_resize_does_not_start_timer_during_manual_resize():
    timer = MagicMock()
    widget = SimpleNamespace(
        _user_adjusting_splitter=True,
        _splitter_resize_in_progress=False,
        _auto_timer=timer,
        _auto_debounce_ms=0,
        _ensure_splitter_hook=MagicMock(),
    )
    ExtraInput._schedule_auto_resize(widget, force=True)
    assert widget._pending_force is True
    widget._ensure_splitter_hook.assert_not_called()
    timer.start.assert_not_called()


def test_auto_resize_tick_consumes_pending_flags():
    widget = SimpleNamespace(
        _pending_force=True,
        _pending_minimize_if_single=True,
        _update_auto_height=MagicMock(),
    )
    ExtraInput._auto_resize_tick(widget)
    assert widget._pending_force is False
    assert widget._pending_minimize_if_single is False
    widget._update_auto_height.assert_called_once_with(force=True, minimize_if_single=True)


def test_auto_resize_tick_swallows_update_errors():
    widget = SimpleNamespace(
        _pending_force=False,
        _pending_minimize_if_single=False,
        _update_auto_height=MagicMock(side_effect=RuntimeError("boom")),
    )
    ExtraInput._auto_resize_tick(widget)
    assert widget._pending_force is False


def test_effective_lines_and_shrink_threshold_are_deterministic():
    assert ExtraInput._effective_lines(SimpleNamespace(), 100, 20, 10) == 4.0
    doc = SimpleNamespace(documentMargin=lambda: 4.0)
    widget = SimpleNamespace(_line_spacing=lambda: 16, document=lambda: doc)
    assert ExtraInput._should_shrink_to_min(widget, 28) is True
    assert ExtraInput._should_shrink_to_min(widget, 29) is False


def test_reset_user_adjusting_flag_and_collapse_to_min():
    widget = SimpleNamespace(_user_adjusting_splitter=True, _schedule_auto_resize=MagicMock())
    ExtraInput._reset_user_adjusting_flag(widget)
    assert widget._user_adjusting_splitter is False
    ExtraInput.collapse_to_min(widget)
    widget._schedule_auto_resize.assert_called_once_with(force=True, enforce_minimize_if_single=True)
