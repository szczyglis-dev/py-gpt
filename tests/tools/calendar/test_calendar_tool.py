from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication, QDate, QEvent
from PySide6.QtWidgets import QMainWindow, QTabWidget
from sqlalchemy import create_engine, text

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools import Tools
from pygpt_net.tools.base import ToolMenuAction
from pygpt_net.tools.calendar import Calendar


@pytest.fixture
def environment(qapp, tmp_path):
    window = QMainWindow()
    db = create_engine('sqlite:///' + str(tmp_path / 'calendar.db'))
    with db.begin() as conn:
        conn.execute(text('''CREATE TABLE calendar_note (
            id INTEGER PRIMARY KEY AUTOINCREMENT, idx INTEGER, uuid TEXT,
            year INTEGER, month INTEGER, day INTEGER, status INTEGER,
            created_ts INTEGER, updated_ts INTEGER, title TEXT, content TEXT,
            is_important BOOLEAN, is_deleted BOOLEAN)'''))
    values = {'font_size': 12, 'ctx.counters.all': True, 'ctx.records.filter': 'all'}
    config = MagicMock()
    config.data = values
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    config.set.side_effect = lambda key, value: values.__setitem__(key, value)
    config.get_lang.return_value = 'en'
    config.has.side_effect = lambda key: key in values
    ctx = MagicMock()
    ctx.provider.get_ctx_count_by_day.return_value = {}
    ctx.provider.get_ctx_labels_count_by_day.return_value = {}
    window.core = SimpleNamespace(config=config, db=SimpleNamespace(get_db=lambda: db), ctx=ctx, debug=MagicMock())
    window.controller = MagicMock()
    window.controller.theme.style.return_value = ''
    window.controller.ui.get_colors.return_value = {}
    window.controller.tabs.get_tabs_by_tool.return_value = []
    window.controller.tabs.get_current_tab.return_value = None
    window.ui = SimpleNamespace(nodes={}, dialog={})
    window.tools = Tools(window)
    tool = Calendar()
    window.tools.register(tool)
    yield tool, window, db
    if tool.dialog is not None:
        tool.dialog.close()
    for session in tuple(tool.sessions):
        session.close()
        session.widget.deleteLater()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
    db.dispose()


def make_tab(column=0):
    tab = Tab()
    tab.type = Tab.TAB_TOOL
    tab.tool_id = 'calendar'
    tab.column_idx = column
    return tab


def select(session, date):
    grid = session.widgets['select']
    grid.setSelectedDate(date)
    grid.on_day_clicked(date)


def test_dialog_is_default_and_singleton_but_tab_is_also_allowed(environment):
    tool, window, db = environment
    assert tool.on_menu_click == ToolMenuAction.ALWAYS_DIALOG
    assert tool.allow_tab and tool.allow_dialog
    assert not tool.multi_tab and not tool.multi_dialog
    action = tool.setup_menu()['calendar']
    action.trigger()
    dialog = tool.dialog
    assert dialog is not None and dialog.isVisible()
    action.trigger()
    assert tool.dialog is dialog
    window.controller.tabs.open_or_activate.assert_not_called()
    tool.open_tab()
    window.controller.tabs.open_or_activate.assert_called_once_with(Tab.TAB_TOOL, 'calendar')
    assert dialog.windowTitle() == 'Calendar'


def test_tab_and_dialog_keep_independent_dates_and_share_persisted_notes(environment):
    tool, window, db = environment
    widget = tool.as_tab(make_tab(1))
    first = widget.session
    second = tool.open().widget.session
    select(first, QDate(2026, 9, 14))
    select(second, QDate(2026, 10, 15))
    first.widgets['note'].setPlainText('September note')
    second.widgets['note'].setPlainText('October note')
    assert tool.storage.load_note(2026, 9, 14) == 'September note'
    assert tool.storage.load_note(2026, 10, 15) == 'October note'
    assert first.widgets['note'].toPlainText() == 'September note'
    assert second.widgets['note'].toPlainText() == 'October note'
    select(second, QDate(2026, 9, 14))
    assert second.widgets['note'].toPlainText() == 'September note'
    first.widgets['note'].setPlainText('Shared edited note')
    assert second.widgets['note'].toPlainText() == 'Shared edited note'
    second.note.update_status(3, 2026, 9, 14)
    assert tool.storage.get_or_load(2026, 9, 14).status == 3
    tool.dialog.close()
    assert second.closed and second not in tool.sessions
    assert not second.widget.filters.clock.timer.isActive()
    assert first in tool.sessions and not first.closed
    widget.on_delete()
    assert not tool.sessions and not tool._surfaces
    reopened = tool.open().widget.session
    select(reopened, QDate(2026, 9, 14))
    assert reopened.widgets['note'].toPlainText() == 'Shared edited note'


def test_headless_copy_to_today_does_not_open_a_frontend(environment):
    tool, window, db = environment
    tool.notes.append_today('first')
    tool.notes.append_today('second')
    today = QDate.currentDate()
    assert tool.storage.load_note(today.year(), today.month(), today.day()) == 'first\nsecond'
    assert not tool.sessions and tool.dialog is None
    with db.connect() as conn:
        assert conn.execute(text('SELECT count(*) FROM calendar_note')).scalar() == 1


def test_legacy_calendar_tabs_restore_as_one_generic_tool_tab(environment, monkeypatch):
    from pygpt_net.core.tabs import Tabs
    tool, window, db = environment
    columns = [QTabWidget(window), QTabWidget(window)]
    window.ui.layout = SimpleNamespace(
        get_column_by_idx=lambda idx: SimpleNamespace(get_tabs=lambda: columns[idx]),
        get_tabs_by_idx=lambda idx: columns[idx])
    core = window.core.tabs = Tabs(window)
    monkeypatch.setattr(core, 'update', lambda: None)
    window.controller.tabs.get_tabs_by_tool.side_effect = lambda tool_id: [
        tab for tab in core.pids.values() if tab.tool_id == tool_id]
    core.restore(dict(uuid='saved-calendar', pid=7, type=Tab.TAB_TOOL_CALENDAR,
                      title='My calendar', data_id=None, column_idx=1, custom_name=True))
    restored = core.pids[7]
    assert restored.type == Tab.TAB_TOOL and restored.tool_id == 'calendar'
    assert restored.uuid == 'saved-calendar' and restored.title == 'My calendar'
    assert restored.column_idx == 1
    assert core.append(Tab.TAB_TOOL, 'calendar', -1, 0) is restored
    assert len(tool.sessions) == 1
    core.remove(restored.pid)
    assert not tool.sessions and not tool._surfaces


def test_browsing_months_does_not_retarget_selected_note_when_another_view_updates(environment):
    tool, window, db = environment
    first = tool.as_tab(make_tab()).session
    second = tool.open().widget.session
    select(first, QDate(2026, 1, 31))
    select(second, QDate(2026, 1, 31))
    first.widgets['note'].setPlainText('January')
    first.widgets['select'].setCurrentPage(2026, 2)
    second.widgets['note'].setPlainText('Updated January')
    assert (first.selected_year, first.selected_month, first.selected_day) == (2026, 1, 31)
    assert first.widgets['note'].toPlainText() == 'Updated January'
    assert tool.storage.load_note(2026, 1, 31) == 'Updated January'


def test_profile_reload_does_not_save_previous_profile_notes_into_new_database(environment, tmp_path):
    tool, window, db = environment
    session = tool.as_tab(make_tab()).session
    select(session, QDate(2026, 9, 14))
    session.widgets['note'].setPlainText('Original profile')
    with db.connect() as conn:
        schema = conn.execute(text("SELECT sql FROM sqlite_master WHERE name='calendar_note'")).scalar()
    new_db = create_engine('sqlite:///' + str(tmp_path / 'other.db'))
    with new_db.begin() as conn:
        conn.execute(text(schema))
    window.core.db.get_db = lambda: new_db
    tool.on_reload()
    assert session.widgets['note'].toPlainText() == ''
    session.widgets['note'].setPlainText('New profile')
    tool.on_exit()
    with db.connect() as conn:
        assert conn.execute(text('SELECT content FROM calendar_note')).scalar() == 'Original profile'
    with new_db.connect() as conn:
        assert conn.execute(text('SELECT content FROM calendar_note')).scalar() == 'New profile'
    window.core.db.get_db = lambda: db
    new_db.dispose()


def test_add_tool_menu_creates_single_calendar_tab_and_hides_when_already_open(environment):
    from PySide6.QtWidgets import QMenu
    from pygpt_net.controller.tools.tools import Tools as ToolsController
    tool, window, db = environment
    window.controller.tabs.get_first_tab_by_tool.return_value = None
    menu = QMenu(window)
    caller = MagicMock()
    submenu = ToolsController(window).append_tab_menu(window, menu, -2, 1, caller)
    assert submenu is not None and len(submenu.actions()) == 1
    assert submenu.actions()[0].text() == 'Calendar'
    submenu.actions()[0].trigger()
    caller.add_tab.assert_called_once_with(-2, 1, Tab.TAB_TOOL, 'calendar')
    window.controller.tabs.get_first_tab_by_tool.return_value = make_tab()
    next_menu = QMenu(window)
    assert ToolsController(window).append_tab_menu(window, next_menu, -2, 0, caller) is None
    assert next_menu.actions() == []


def test_status_change_keeps_saved_note_content_even_when_not_cached(environment):
    tool, window, db = environment
    tool.storage.update_note(2026, 1, 31, 'Keep this content')
    session = tool.as_tab(make_tab()).session
    tool.storage.reset()
    session.note.update_status(4, 2026, 1, 31)
    assert tool.storage.load_note(2026, 1, 31) == 'Keep this content'
    assert tool.storage.get_or_load(2026, 1, 31).status == 4
