from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMainWindow
from sqlalchemy import create_engine, text

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.notepad import Notepad


def database(path):
    engine = create_engine('sqlite:///' + str(path))
    with engine.begin() as connection:
        connection.execute(text('''CREATE TABLE notepad (
            id INTEGER PRIMARY KEY, idx INTEGER UNIQUE, uuid TEXT, title TEXT,
            content TEXT, created_ts INTEGER, updated_ts INTEGER,
            is_deleted INTEGER, is_initialized INTEGER, highlights_json TEXT,
            scroll_pos INTEGER)'''))
    return engine


@pytest.fixture
def environment(qapp, tmp_path):
    window = QMainWindow()
    db = database(tmp_path / 'first.db')
    config = MagicMock()
    config.data = {'font_size': 12}
    config.get.side_effect = lambda key, default=None: {'font_size': 12, 'theme': 'dark'}.get(key, default)
    window.core = SimpleNamespace(config=config, db=SimpleNamespace(get_db=lambda: db))
    window.controller = MagicMock()
    window.controller.theme.common.normalize_theme.side_effect = lambda theme: theme
    window.controller.tabs.get_tabs_by_tool.return_value = []
    window.ui = SimpleNamespace(nodes={})
    window.dispatch = MagicMock()
    tool = Notepad()
    tool.attach(window)
    window.tools = {'notepad': tool}
    yield tool, window, db
    for document in tuple(tool.documents.opened.values()):
        widget = document.widget
        document.close()
        if widget is not None:
            widget.deleteLater()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)
    db.dispose()


def make_tab(idx=None, title='', column=0):
    tab = Tab()
    tab.type = Tab.TAB_TOOL
    tab.tool_id = 'notepad'
    tab.data_id = idx
    tab.title = title
    tab.column_idx = column
    return tab


def rows(db):
    with db.connect() as connection:
        return {row.idx: row._asdict() for row in connection.execute(text('SELECT * FROM notepad'))}


def test_independent_documents_save_markers_and_closed_note_text(environment, qapp):
    tool, window, db = environment
    first = tool.as_tab(make_tab(title='First', column=1))
    second = tool.as_tab(make_tab(title='Second'))
    assert first.id != second.id
    tool.documents.append('abcdef', first.id)
    first.textarea.markers.restore([(1, 3)])
    tool.documents.append('other', second.id)
    tool.documents.save_all()
    assert rows(db)[first.id]['content'] == 'abcdef'
    assert rows(db)[second.id]['content'] == 'other'
    first.on_delete()
    assert first.id not in tool.documents.widgets
    assert not first.textarea.save_timer.isActive()
    assert not first.textarea.finder.timer.isActive()
    assert first.textarea.finder.textarea is None
    window.controller.finder.unset.assert_called_with(first.textarea.finder)
    tool.documents.append('tail', first.id)
    assert tool.documents.text(first.id) == 'abcdef\ntail'
    restored = tool.as_tab(make_tab(first.id, 'First'))
    assert restored.textarea.toPlainText() == 'abcdef\ntail'
    assert restored.textarea.markers.ranges() == [(1, 3)]
    assert rows(db)[second.id]['content'] == 'other'


def test_close_flushes_pending_autosave_and_profile_switch_uses_own_database(environment, tmp_path):
    tool, window, first_db = environment
    first = tool.as_tab(make_tab(1, 'Old profile'))
    first.textarea.setPlainText('old pending change')
    assert first.textarea.save_timer.isActive()
    second_db = database(tmp_path / 'second.db')
    window.core.db.get_db = lambda: second_db
    first.on_delete()
    assert rows(first_db)[1]['content'] == 'old pending change'
    assert rows(second_db) == {}
    second = tool.as_tab(make_tab(1, 'New profile'))
    assert second.toPlainText() == ''
    tool.documents.append('new content', second.id)
    tool.on_reload()
    assert second.toPlainText() == 'new content'
    assert rows(second_db)[1]['content'] == 'new content'
    assert rows(first_db)[1]['content'] == 'old pending change'
    second.on_delete()
    second_db.dispose()


def test_autosave_and_reopening_saved_note(environment):
    tool, window, db = environment
    tab = make_tab(column=1)
    widget = tool.as_tab(tab)
    editor = widget.textarea
    editor.setPlainText('typed note')
    assert editor.save_timer.isActive()
    editor.save_timer.stop()
    editor.save_timer.timeout.emit()
    assert rows(db)[widget.id]['content'] == 'typed note'
    tool.setup_theme()
    widget.on_delete()
    other = tool.as_tab(make_tab())
    assert other.id == widget.id
    assert other.toPlainText() == 'typed note'
    assert not editor.view.focus_timer.isActive()
    assert not editor.view.restore_timer.isActive()
    assert not tool.documents.opened[other.id].loading


def test_storage_cache_refresh_and_default_tab_export(environment, tmp_path):
    tool, window, db = environment
    doc = tool.documents.create(7)
    doc.append('saved')
    doc.close()
    exported = tool.storage.import_from_db()[7]
    assert exported['data_id'] == 7
    assert exported['type'] == Tab.TAB_TOOL
    assert exported['tool_id'] == 'notepad'
    assert tool.allow_tab and tool.multi_tab and not tool.allow_dialog
    second_db = database(tmp_path / 'next.db')
    window.core.db.get_db = lambda: second_db
    assert tool.storage.get_all() == {}
    second_db.dispose()


def test_restore_is_silent_and_preserves_saved_scroll_before_widget_is_shown(environment):
    tool, window, db = environment
    item = tool.storage.allocate(4)
    item.content = 'long note\n' * 150
    item.highlights = [(0, 4)]
    item.scroll_pos = 80
    tool.storage.writer().save(item)
    widget = tool.as_tab(make_tab(4, 'Saved'))
    assert not widget.textarea.save_timer.isActive()
    assert widget.textarea.view.pending_scroll == 80
    document = tool.documents.opened[4]
    document.save()
    assert rows(db)[4]['scroll_pos'] == 80
    tool.on_selected(widget.tab)
    assert document.opened
    assert widget.textarea.view.pending_scroll == 80


def test_real_editor_context_menu_marks_and_unmarks(environment, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QTextCursor
    from PySide6.QtWidgets import QMenu
    tool, window, db = environment
    widget = tool.as_tab(make_tab(title='Menu note'))
    editor = widget.textarea
    editor.setPlainText('hello world')
    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(5, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    captured = []

    class NonBlockingMenu(QMenu):
        def exec(self, *args):
            captured.append(self)

    editor.createStandardContextMenu = lambda: NonBlockingMenu(editor)
    window.ui.context_menu = SimpleNamespace(
        get_copy_to_menu=lambda *args, **kwargs: QMenu(editor),
        get_insert_datetime_menu=lambda *args: QMenu(editor),
        get_zoom_menu=lambda *args: QMenu(editor))
    monkeypatch.setattr('pygpt_net.tools.notepad.ui.menus.trans', lambda key: key)
    editor.menus.context(SimpleNamespace(globalPos=lambda: QPoint()))
    next(action for action in captured[-1].actions() if action.text() == 'action.mark').trigger()
    assert editor.markers.ranges() == [(0, 5)]
    assert rows(db)[widget.id]['highlights_json'] == '[[0, 5]]'
    editor.menus.context(SimpleNamespace(globalPos=lambda: QPoint()))
    action = next(action for action in captured[-1].actions() if action.text() == 'action.unmark')
    assert action.isEnabled()
    action.trigger()
    assert editor.markers.ranges() == []


def test_core_tabs_create_move_restore_and_close_real_notepads(environment, monkeypatch):
    import uuid
    from PySide6.QtWidgets import QTabWidget
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
    first = core.append(Tab.TAB_TOOL, 'notepad', -1, 0)
    second = core.append(Tab.TAB_TOOL, 'notepad', -1, 1)
    assert first.data_id != second.data_id
    assert first.title.endswith(' 1') and second.title.endswith(' 2')
    tool.documents.append('first content', first.data_id)
    core.update_title(first.idx, 'Named note', 'Named note', first.column_idx)
    core.remove(first.pid)
    assert first.data_id not in tool.documents.widgets
    assert rows(db)[first.data_id]['title'] == 'Named note'
    identity = uuid.uuid4()
    core.restore(dict(uuid=identity, pid=9, type=Tab.TAB_NOTEPAD,
                                 title='Named note', data_id=first.data_id,
                                 column_idx=1, custom_name=True))
    restored = core.pids[9]
    assert restored.type == Tab.TAB_TOOL and restored.uuid == identity
    assert tool.documents.text(restored.data_id) == 'first content'
    assert tool.documents.widgets[restored.data_id].tab is restored
    core.move_tab(restored, 0)
    assert restored.column_idx == 0
    assert tool.documents.widgets[restored.data_id].textarea.tab.column_idx == 0
    core.remove(restored.pid)
    assert second.data_id in tool.documents.widgets
    core.remove(second.pid)
    assert not tool.documents.widgets and not tool._surfaces


def test_open_saved_note_preserves_document_id(environment):
    tool, window, db = environment
    document = tool.documents.create(6)
    document.append('saved closed note')
    document.close()
    window.controller.tabs.get_current_column_idx.return_value = 1
    tool.tabs.open(6)
    window.controller.tabs.append.assert_called_once_with(
        type=Tab.TAB_TOOL, tool_id='notepad', idx=-2, column_idx=1, data_id=6)


def test_microphone_status_is_owned_by_clicked_notepad(environment):
    from pygpt_net.controller.audio.ui import UI
    tool, window, db = environment
    first = tool.as_tab(make_tab(title='First'))
    second = tool.as_tab(make_tab(title='Second'))
    window.ui.plugin_addon = {}
    window.ui.nodes['input'] = MagicMock()
    window.controller.audio.is_recording.return_value = False
    audio_ui = window.controller.audio.ui = UI(window)
    window.controller.tabs.get_current_tab.return_value = second.tab
    first.mic_button.click()
    assert first.record_status._state == 'pending'
    assert second.record_status._state == 'idle'
    audio_ui.on_input_begin('input')
    assert first.record_status._state == 'recording'
    assert second.record_status._state == 'idle'
    tool.apply_lang_mappings()
    assert audio_ui.is_recording_in(first)
    assert not audio_ui.is_recording_in(second)
    audio_ui.on_input_end('input')
    assert first.record_status._state == second.record_status._state == 'idle'


def test_add_menu_uses_notepad_hook_without_duplicate_and_preserves_column(environment):
    from PySide6.QtWidgets import QMenu
    from pygpt_net.controller.tools.tools import Tools
    from pygpt_net.tools.base import BaseTool
    tool, window, db = environment
    ordinary = BaseTool()
    ordinary.id = 'ordinary'
    ordinary.allow_tab = True
    ordinary.tab_title = 'Ordinary'
    ordinary.attach(window)
    window.tools = SimpleNamespace(get_all=lambda: {'notepad': tool, 'ordinary': ordinary})
    caller = MagicMock()
    menu = QMenu(window)
    submenu = Tools(window).append_tab_menu(window, menu, -2, 1, caller)
    assert len(menu.actions()) == 2
    assert len(submenu.actions()) == 1
    assert submenu.actions()[0].text() == 'Ordinary'
    menu.actions()[0].trigger()
    caller.add_tab.assert_called_once_with(-2, 1, Tab.TAB_TOOL, 'notepad')
    menu.deleteLater()


def test_adding_after_close_all_restores_slots_from_database(environment):
    tool, window, db = environment
    first = tool.as_tab(make_tab(title='First saved', column=0))
    second = tool.as_tab(make_tab(title='Second saved', column=1))
    assert (first.id, second.id) == (1, 2)
    first.textarea.setPlainText('first pending content')
    first.textarea.markers.restore([(0, 5)])
    second.textarea.setPlainText('second pending content')
    first.on_delete()
    second.on_delete()
    assert not tool.documents.opened
    # Discard cached items so this checks actual persistence, not just memory.
    tool.storage.reset()
    restored_first = tool.as_tab(make_tab(column=1))
    restored_second = tool.as_tab(make_tab(column=0))
    assert (restored_first.id, restored_second.id) == (1, 2)
    assert restored_first.toPlainText() == 'first pending content'
    assert restored_second.toPlainText() == 'second pending content'
    assert restored_first.tab.title == 'First saved'
    assert restored_second.tab.title == 'Second saved'
    assert restored_first.textarea.markers.ranges() == [(0, 5)]
    third = tool.as_tab(make_tab())
    assert third.id == 3
    assert third.toPlainText() == ''


def test_reopening_lowest_free_slot_does_not_reuse_an_open_note(environment):
    tool, window, db = environment
    first = tool.as_tab(make_tab())
    second = tool.as_tab(make_tab(column=1))
    third = tool.as_tab(make_tab())
    tool.documents.append('saved second', second.id)
    tool.documents.append('still open third', third.id)
    second.on_delete()
    reopened = tool.as_tab(make_tab())
    assert reopened.id == 2
    assert reopened.toPlainText() == 'saved second'
    assert first.id == 1 and third.id == 3
    assert third.toPlainText() == 'still open third'
    fourth = tool.as_tab(make_tab())
    assert fourth.id == 4
