"""Regression coverage for browsing directory matches during recursive search."""
import threading
from collections import deque
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.tools.files.ui.search import TreeSearch, find_paths, _path_key


def _files(root):
    nested = root / "project" / "assets" / "images"
    nested.mkdir(parents=True)
    (nested / "logo.txt").write_text("logo")
    (root / "unrelated").mkdir()
    (root / "unrelated" / "hidden.txt").write_text("hidden")
    return nested


def test_directory_match_exposes_descendants_without_autoexpanding_them(tmp_path):
    nested = _files(tmp_path)

    accepted, directories = find_paths(str(tmp_path), "project")

    assert str(nested / "logo.txt") in accepted
    assert str(nested) in accepted
    assert str(nested.parent) in accepted
    assert str(tmp_path / "unrelated") not in accepted
    assert directories == {str(tmp_path), str(tmp_path / "project")}


def test_file_match_retains_ancestors_but_not_their_unmatched_contents(tmp_path):
    nested = _files(tmp_path)
    (nested / "other.txt").write_text("other")

    accepted, directories = find_paths(str(tmp_path), "logo")

    assert str(nested / "logo.txt") in accepted
    assert str(nested / "other.txt") not in accepted
    assert directories == {str(tmp_path), str(nested), str(nested.parent), str(nested.parent.parent)}


def test_cancelled_search_does_not_publish_partial_results(tmp_path):
    _files(tmp_path)
    cancelled = threading.Event()
    cancelled.set()
    assert find_paths(str(tmp_path), "project", cancelled) is None


def test_lazy_directory_notifications_do_not_restart_search():
    search = SimpleNamespace(
        loaded_directories=set(), apply_timer=MagicMock(), files_changed=MagicMock(),
        explorer=SimpleNamespace(model=SimpleNamespace(filePath=lambda index: index)),
    )
    TreeSearch.rows_inserted(search, '/project/assets')
    search.apply_timer.start.assert_called_once_with(0)
    search.files_changed.assert_not_called()
    TreeSearch.directory_loaded(search, '/project/assets')
    assert _path_key('/project/assets') in search.loaded_directories
    TreeSearch.rows_inserted(search, '/project/assets')
    search.files_changed.assert_called_once_with()


def test_scan_counts_matches_in_worker_and_keeps_relative_unicode_patterns(tmp_path):
    nested = _files(tmp_path)
    path = nested / 'Zażółć.TXT'
    path.write_text('text')
    accepted, directories, count = find_paths(str(tmp_path), 'project/assets/images/*.txt', include_count=True)
    assert count == 2
    assert str(path) in accepted
    assert str(nested) in directories
    assert find_paths(str(tmp_path), 'ZAŻÓŁĆ', include_count=True)[2] == 1
    assert find_paths(str(tmp_path), 'project', include_count=True)[2] == 1


def test_scan_can_cancel_inside_large_directory(monkeypatch, tmp_path):
    from pygpt_net.tools.files.ui import search as module
    monkeypatch.setattr(module.os, 'walk', lambda *a, **kw: [(str(tmp_path), [], ['file.txt'] * 10000)])

    class CancelDuringScan:
        checks = 0

        def is_set(self):
            self.checks += 1
            return self.checks > 10

    cancelled = CancelDuringScan()
    assert find_paths(str(tmp_path), '*.txt', cancelled) is None
    assert cancelled.checks == 11


def test_large_result_application_batches_and_cancels_without_event_loop(qapp, tmp_path):
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    model = QStandardItemModel()
    root_item = QStandardItem(str(tmp_path))
    model.appendRow(root_item)
    for number in range(600):
        root_item.appendRow(QStandardItem(str(tmp_path / f'{number}.txt')))
    root = model.index(0, 0)
    filesystem = SimpleNamespace(
        index=lambda *args: root if isinstance(args[0], str) else model.index(*args),
        rowCount=model.rowCount, filePath=lambda index: index.data(), isDir=lambda index: False,
    )
    hidden = {}
    tree = MagicMock()
    tree.updatesEnabled.return_value = True
    tree.isRowHidden.side_effect = lambda row, parent: hidden.get(row, False)
    tree.setRowHidden.side_effect = lambda row, parent, value: hidden.__setitem__(row, value)
    search = SimpleNamespace(
        explorer=SimpleNamespace(model=filesystem, treeView=tree, directory=str(tmp_path)),
        pending=False, collapse_on_apply=False, _applying=False, _reapply=False,
        _apply_queue=deque(), accepted={str(tmp_path)}, directories=set(),
        _accepted_keys_token=None, _directory_keys_token=None,
        batch_timer=MagicMock(), apply_timer=MagicMock(),
        _restore_normal_view=MagicMock(),
    )
    search._refresh_path_keys = lambda: TreeSearch._refresh_path_keys(search)
    search.apply_batch = lambda: TreeSearch.apply_batch(search)
    search.stop_applying = lambda: TreeSearch.stop_applying(search)
    TreeSearch.apply(search)
    assert search._applying
    search.batch_timer.start.assert_called_with(1)
    while search._applying:
        search.apply_batch()
    assert len(hidden) == 600 and all(hidden.values())
    search.accepted = None
    TreeSearch.apply(search)
    assert search._applying
    search.pending = True
    search.apply_batch()
    assert not search._applying
    assert not search._apply_queue
    search.batch_timer.stop.assert_called_once_with()
    search.pending = False
    TreeSearch.apply(search)
    while search._applying:
        search.apply_batch()
    assert not any(hidden.values())
