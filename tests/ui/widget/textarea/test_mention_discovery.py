import os
import threading
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEventLoop, QTimer, QThread

from pygpt_net.core.filesystem.local_mapper import LocalPathMapper
from pygpt_net.ui.widget.textarea.mention_discovery import ScanSpec, WorkdirScan, WorkdirMentionDiscovery


def spec_for(root, **kwargs):
    root = str(root)
    return ScanSpec(root, LocalPathMapper(root, root, root, ()), **kwargs)


def run_scan(spec):
    worker = WorkdirScan(spec)
    results = []
    worker.signals.ready.connect(lambda _worker, entries, complete: results.append((entries, complete)))
    worker.run()
    assert results[-1][1]
    return results[-1][0]


def wait_for_update(discovery):
    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    discovery.updated.connect(loop.quit)
    timer.start(3000)
    loop.exec()
    discovery.updated.disconnect(loop.quit)
    assert timer.isActive(), 'Background discovery did not finish'
    timer.stop()


def test_scan_preserves_nested_paths_and_prunes_symlinks_blacklist(tmp_path):
    (tmp_path / 'sub').mkdir()
    for name in ('first.txt', 'sub/note.txt', 'sub/excluded.EXE', 'sub/reserved.txt', 'bad\nname.txt'):
        (tmp_path / name).write_text('')
    (tmp_path / 'linked-file').symlink_to(tmp_path / 'first.txt')
    (tmp_path / 'sub/loop').symlink_to(tmp_path, target_is_directory=True)
    entries = run_scan(spec_for(tmp_path, excluded_extensions=frozenset({'exe'}),
                               excluded_paths=frozenset({str(tmp_path / 'sub/reserved.txt')})))
    assert [e.label for e in entries] == ['first.txt', 'sub/note.txt']
    assert [e.value for e in entries] == ['%workdir%/data/first.txt', '%workdir%/data/sub/note.txt']


def test_scan_limit_and_inaccessible_directory(tmp_path, monkeypatch):
    (tmp_path / 'denied').mkdir()
    (tmp_path / 'ok').mkdir()
    for i in range(8):
        (tmp_path / 'ok' / f'{i}.txt').write_text('')
    original = os.scandir
    def scandir(path):
        if str(path).endswith('denied'):
            raise PermissionError(path)
        return original(path)
    monkeypatch.setattr(os, 'scandir', scandir)
    assert len(run_scan(spec_for(tmp_path, limit=3))) == 3


def test_discovery_does_not_walk_on_ui_thread_and_reuses_inflight_and_cache(tmp_path, monkeypatch, qt_application):
    (tmp_path / 'note.txt').write_text('')
    original = os.scandir
    entered, release = threading.Event(), threading.Event()
    threads = []
    def scandir(path):
        threads.append(QThread.currentThread())
        entered.set()
        assert release.wait(3)
        return original(path)
    monkeypatch.setattr(os, 'scandir', scandir)
    discovery = WorkdirMentionDiscovery()
    spec = spec_for(tmp_path)
    assert discovery.entries(spec) == []
    assert entered.wait(3)
    worker = discovery._worker
    assert discovery.entries(spec) == []
    assert discovery._worker is worker
    assert all(t != qt_application.thread() for t in threads)
    # The UI event loop can release a blocked filesystem worker.
    QTimer.singleShot(0, release.set)
    wait_for_update(discovery)
    assert discovery._worker is None
    assert [e.label for e in discovery.entries(spec)] == ['note.txt']
    assert len(threads) == 1


def test_expired_cache_returns_old_results_while_refreshing(tmp_path, qt_application):
    (tmp_path / 'old.txt').write_text('')
    discovery = WorkdirMentionDiscovery()
    spec = spec_for(tmp_path)
    discovery.entries(spec)
    wait_for_update(discovery)
    discovery.CACHE_SECONDS = 0
    (tmp_path / 'new.txt').write_text('')
    assert [e.label for e in discovery.entries(spec)] == ['old.txt']
    wait_for_update(discovery)
    discovery.CACHE_SECONDS = 30
    assert [e.label for e in discovery.entries(spec)] == ['new.txt', 'old.txt']


def test_project_change_cancels_and_discards_old_results(tmp_path):
    discovery = WorkdirMentionDiscovery()
    discovery._pool = MagicMock()
    first = spec_for(tmp_path / 'first')
    second = spec_for(tmp_path / 'second')
    discovery.entries(first)
    previous = discovery._worker
    discovery.entries(second)
    assert previous.cancelled.is_set()
    discovery._on_ready(previous, ['obsolete'], True)
    assert first not in discovery._cache
    current = discovery._worker
    discovery._on_ready(current, ['current'], True)
    assert discovery.entries(second) == ['current']
    assert discovery._pool.start.call_count == 2


def test_filter_change_starts_new_scan_and_destroy_cancels(tmp_path):
    from shiboken6 import delete
    discovery = WorkdirMentionDiscovery()
    discovery._pool = MagicMock()
    first = spec_for(tmp_path)
    discovery.entries(first)
    worker = discovery._worker
    discovery.entries(spec_for(tmp_path, excluded_extensions=frozenset({'txt'})))
    assert worker.cancelled.is_set()
    worker = discovery._worker
    delete(discovery)
    assert worker.cancelled.is_set()


@pytest.mark.parametrize('dismissed', [False, True])
def test_background_update_keeps_current_query_and_respects_dismissal(qt_application, dismissed):
    from PySide6.QtWidgets import QTextEdit
    from pygpt_net.ui.widget.textarea.input import ChatInput
    from pygpt_net.ui.widget.textarea.mention import MentionPopup, MentionEntry
    from pygpt_net.core.text.mentions import KIND_FILE_CONTEXT
    from types import SimpleNamespace

    class Editor(QTextEdit):
        _on_workdir_mentions_updated = ChatInput._on_workdir_mentions_updated
        _refresh_mention_popup = ChatInput._refresh_mention_popup

    editor = Editor()
    editor.setPlainText('@nested')
    editor._mention_popup = MentionPopup(editor)
    editor._mention_loading = False
    editor._mention_dismissed = dismissed
    editor._mention_button_cursor = None
    editor._mention_trigger_pos = 0
    editor._mention_source_key = 'old'
    editor.hasFocus = lambda: True
    editor._find_mention_trigger = lambda: (0, 7, 'nested')
    editor._get_mention_source_key = lambda: 'new'
    editor._get_conversation_mention_entries = lambda query: []
    editor._build_mention_entries = MagicMock(return_value=[
        MentionEntry(KIND_FILE_CONTEXT, 'root.txt', 'root.txt'),
        MentionEntry(KIND_FILE_CONTEXT, 'nested/note.txt', 'nested/note.txt'),
    ])
    core = MagicMock()
    core.ctx.get_current_meta.return_value = None
    editor.window = SimpleNamespace(core=core)
    editor._mention_popup.show_above = MagicMock()
    editor._on_workdir_mentions_updated()
    if dismissed:
        editor._mention_popup.show_above.assert_not_called()
        editor._build_mention_entries.assert_not_called()
    else:
        files = [editor._mention_popup.list.item(i).data(MentionPopup.ROLE_ENTRY)
                 for i in range(editor._mention_popup.list.count())]
        assert [entry.label for entry in files if entry and entry.kind == KIND_FILE_CONTEXT] == ['nested/note.txt']
        assert editor.toPlainText() == '@nested'
        editor._mention_popup.show_above.assert_called_once()
    editor.close()


def test_partial_results_reuse_worker_and_cache_stays_bounded(tmp_path):
    discovery = WorkdirMentionDiscovery()
    discovery._pool = MagicMock()
    for i in range(discovery.CACHE_ROOTS + 2):
        spec = spec_for(tmp_path / str(i))
        discovery.entries(spec)
        worker = discovery._worker
        discovery._on_ready(worker, [f'partial-{i}'], False)
        assert discovery.entries(spec) == [f'partial-{i}']
        assert discovery._worker is worker
        discovery._on_ready(worker, [f'complete-{i}'], True)
    assert len(discovery._cache) == discovery.CACHE_ROOTS
    assert spec_for(tmp_path / '0') not in discovery._cache
    assert discovery._pool.start.call_count == discovery.CACHE_ROOTS + 2


def test_cancelled_worker_does_not_touch_filesystem(tmp_path, monkeypatch):
    scan = MagicMock()
    monkeypatch.setattr(os, 'scandir', scan)
    worker = WorkdirScan(spec_for(tmp_path))
    worker.cancel()
    worker.run()
    scan.assert_not_called()
