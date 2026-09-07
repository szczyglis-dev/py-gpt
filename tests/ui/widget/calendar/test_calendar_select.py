from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QDate
from PySide6.QtGui import QColor

from pygpt_net.ui.widget.calendar.select import CalendarSelect


def test_set_tab_and_page_change_update_state_and_controller():
    window = MagicMock()
    widget = SimpleNamespace(tab=None, currentYear=0, currentMonth=0, window=window)
    tab = SimpleNamespace(column_idx=2)

    CalendarSelect.set_tab(widget, tab)
    CalendarSelect.page_changed(widget, 2026, 9)

    assert widget.tab is tab
    assert (widget.currentYear, widget.currentMonth) == (2026, 9)
    window.controller.calendar.on_page_changed.assert_called_once_with(2026, 9)


def test_theme_cache_updates_only_when_theme_changes():
    config = MagicMock()
    config.get.side_effect = ["dark", "dark", "light"]
    widget = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(config=config)),
        _theme_cached=None,
        _counter_bg=QColor(), _counter_font=QColor(),
    )

    CalendarSelect._update_theme_cache(widget)
    assert widget._theme_cached == "dark"
    assert widget._counter_bg == QColor(70, 70, 70)
    assert widget._counter_font == QColor(255, 255, 255)

    first_bg = widget._counter_bg
    CalendarSelect._update_theme_cache(widget)
    assert widget._counter_bg == first_bg

    CalendarSelect._update_theme_cache(widget)
    assert widget._theme_cached == "light"
    assert widget._counter_bg == QColor(200, 200, 200)


def test_get_color_for_status_uses_mapping_or_defaults():
    mapped_bg = QColor(1, 2, 3)
    mapped_font = QColor(4, 5, 6)
    window = MagicMock()
    window.controller.ui.get_colors.return_value = {2: {"color": mapped_bg, "font": mapped_font}}
    widget = SimpleNamespace(window=window, _default_status_bg="bg", _default_status_font="font")

    assert CalendarSelect.get_color_for_status(widget, 2) == (mapped_bg, mapped_font)
    assert CalendarSelect.get_color_for_status(widget, 99) == ("bg", "font")


def test_day_click_updates_date_and_dispatches_both_calendar_actions_and_focus():
    date = QDate(2026, 9, 7)
    window = MagicMock()
    widget = SimpleNamespace(currentYear=0, currentMonth=0, currentDay=0, window=window, tab=SimpleNamespace(column_idx=3))

    CalendarSelect.on_day_clicked(widget, date)

    assert (widget.currentYear, widget.currentMonth, widget.currentDay) == (2026, 9, 7)
    window.controller.calendar.on_day_select.assert_called_once_with(2026, 9, 7)
    window.controller.calendar.on_ctx_select.assert_called_once_with(2026, 9, 7)
    window.controller.ui.tabs.on_column_focus.assert_called_once_with(3)


def test_add_ctx_stores_string_counter_and_updates_only_cell():
    date = QDate(2026, 9, 7)
    widget = SimpleNamespace(counters={"ctx": {}}, updateCell=MagicMock())

    CalendarSelect.add_ctx(widget, date, 12)

    assert widget.counters["ctx"][date] == "12"
    widget.updateCell.assert_called_once_with(date)


def test_update_ctx_and_notes_parse_iso_dates_without_local_timezone_dependency():
    widget = SimpleNamespace(counters={"ctx": {}, "notes": {}}, labels={}, updateCells=MagicMock())

    CalendarSelect.update_ctx(widget, {"2026-09-07": 2}, {"2026-09-07": [1, 2]})
    CalendarSelect.update_notes(widget, {"2026-09-08": {1: 1}})

    assert widget.counters["ctx"][QDate(2026, 9, 7)] == 2
    assert widget.labels[QDate(2026, 9, 7)] == [1, 2]
    assert widget.counters["notes"][QDate(2026, 9, 8)] == {1: 1}
    assert widget.updateCells.call_count == 2


def test_execute_action_and_set_label_for_day_use_explicit_date_parts():
    date = QDate(2026, 9, 7)
    window = MagicMock()
    widget = SimpleNamespace(window=window)

    CalendarSelect.execute_action(widget, date)
    CalendarSelect.set_label_for_day(widget, date, 4)

    window.controller.calendar.on_ctx_select.assert_called_once_with(2026, 9, 7)
    window.controller.calendar.note.update_status.assert_called_once_with(4, 2026, 9, 7)


def test_context_menu_event_delegates_position():
    event = MagicMock()
    event.pos.return_value = "point"
    widget = SimpleNamespace(open_context_menu=MagicMock())
    CalendarSelect.contextMenuEvent(widget, event)
    widget.open_context_menu.assert_called_once_with("point")
