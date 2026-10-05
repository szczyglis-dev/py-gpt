from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from pygpt_net.core.text.mentions import KIND_CONVERSATION
from pygpt_net.provider.core.ctx.db_sqlite.storage import Storage
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.mention import MentionEntry, MentionPopup
from pygpt_net.ui.widget.textarea.mention_discovery import ConversationTitleDiscovery, ConversationTitleScan
from tests.ui.widget.textarea.test_mention_discovery import complete_scan


@pytest.fixture
def history_db(tmp_path):
    db = create_engine('sqlite:///' + str(tmp_path / 'history.db'))
    with db.begin() as conn:
        conn.execute(text('CREATE TABLE ctx_meta (id INTEGER PRIMARY KEY, name TEXT, '
                          'is_deleted INTEGER, root_id INTEGER, updated_ts INTEGER)'))
        conn.execute(text('INSERT INTO ctx_meta VALUES '
                          "(1, 'Plan podróży', 0, NULL, 1), "
                          "(2, 'ŻÓŁW i jeż', 0, 0, 2), "
                          "(3, 'Plan domu', 0, NULL, 3), "
                          "(4, 'Usunięty plan', 1, NULL, 4), "
                          "(5, 'Plan pod-agenta', 0, 1, 5), "
                          "(6, NULL, 0, NULL, 6), "
                          "(7, 'Plan 100%_done', 0, NULL, 7)"))
    yield db
    db.dispose()


def widget_for(discovery, db):
    core = SimpleNamespace(db=SimpleNamespace(get_db=lambda: db),
                           ctx=SimpleNamespace(get_meta_by_id=MagicMock()), debug=SimpleNamespace(log=MagicMock()))
    widget = SimpleNamespace(window=SimpleNamespace(core=core), _conversation_discovery=discovery)
    widget._get_conversation_mention_entry = lambda query: ChatInput._get_conversation_mention_entry(widget, query)
    return widget


def test_title_scan_reads_only_base_undeleted_history(history_db):
    assert [ctx_id for ctx_id, _ in Storage.iter_meta_titles(history_db)] == [7, 6, 3, 2, 1]
    worker = ConversationTitleScan(history_db)
    results = []
    worker.signals.ready.connect(lambda _worker, batch, done: results.append((batch, done)))
    worker.run()
    titles, complete = results[-1]
    assert complete
    assert [entry.value for entry, _ in titles] == ['7', '3', '2', '1']
    assert all(entry.kind == KIND_CONVERSATION for entry, _ in titles)


@pytest.mark.parametrize('query, expected', [('PLAN', ['7', '3', '1']), ('podró', ['1']),
                                            ('żółw', ['2']), ('100%_', ['7']), ('missing', [])])
def test_title_search_uses_full_history_unicode_and_literal_fragments(history_db, qt_application, query, expected):
    discovery = ConversationTitleDiscovery()
    discovery._pool = MagicMock()
    widget = widget_for(discovery, history_db)
    assert ChatInput._get_conversation_mention_entries(widget, query) == []
    complete_scan(discovery)
    entries = ChatInput._get_conversation_mention_entries(widget, query)
    assert [entry.value for entry in entries] == expected
    assert discovery._worker is None
    widget.window.core.ctx.get_meta_by_id.assert_not_called()
    # Mentions use stable IDs while rendering the selected conversation title.
    if entries:
        popup = MentionPopup()
        popup.set_entries(entries, query=query)
        shown = [popup.list.item(i).data(popup.ROLE_ENTRY) for i in range(popup.list.count())]
        assert [entry.value for entry in shown if entry and entry.kind == KIND_CONVERSATION]
        popup.close()


@pytest.mark.parametrize('query', ['', ' ', ' plan', 'plan ', '123 '])
def test_empty_or_finished_token_does_not_scan_history(query):
    discovery = MagicMock()
    widget = widget_for(discovery, MagicMock())
    assert ChatInput._get_conversation_mention_entries(widget, query) == []
    discovery.entries.assert_not_called()


@pytest.mark.parametrize('deleted', [False, True])
def test_exact_numeric_id_is_available_before_title_scan_finishes(deleted):
    discovery = MagicMock()
    discovery.entries.return_value = []
    widget = widget_for(discovery, MagicMock())
    widget.window.core.ctx.get_meta_by_id.return_value = SimpleNamespace(name='Plan domu', deleted=deleted)
    entries = ChatInput._get_conversation_mention_entries(widget, '123')
    assert entries == ([] if deleted else [MentionEntry(KIND_CONVERSATION, 'Plan domu', '123')])
    widget.window.core.ctx.get_meta_by_id.assert_called_once_with(123)
    discovery.entries.assert_called_once()


def test_title_results_are_bounded_before_display():
    discovery = MagicMock()
    discovery.entries.return_value = [(MentionEntry(KIND_CONVERSATION, f'Plan {i}', str(i)), f'plan {i}')
                                      for i in range(1000)]
    entries = ChatInput._get_conversation_mention_entries(widget_for(discovery, MagicMock()), 'plan')
    assert len(entries) == MentionPopup.MAX_RESULTS


def test_numeric_title_fragments_keep_exact_id_first_and_deduplicate():
    exact = MentionEntry(KIND_CONVERSATION, 'Z plan 123', '123')
    other = MentionEntry(KIND_CONVERSATION, 'A plan 123', '8')
    discovery = MagicMock()
    discovery.entries.return_value = [(other, other.label.casefold()), (exact, exact.label.casefold())]
    widget = widget_for(discovery, MagicMock())
    widget.window.core.ctx.get_meta_by_id.return_value = SimpleNamespace(name=exact.label, deleted=False)
    entries = ChatInput._get_conversation_mention_entries(widget, '123')
    assert entries == [exact, other]
    popup = MentionPopup()
    popup.set_entries(entries, query='123')
    shown = [popup.list.item(i).data(popup.ROLE_ENTRY) for i in range(popup.list.count())]
    assert [entry for entry in shown if entry and entry.kind == KIND_CONVERSATION] == [exact, other]
    popup.close()
