"""Regression coverage for browsing directory matches during recursive search."""
import threading
import time

from PySide6.QtCore import QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileSystemModel, QLabel, QLineEdit, QTreeView, QWidget

from pygpt_net.ui.widget.filesystem.search import TreeSearch, find_paths


def _wait_until(predicate, timeout=5000):
    deadline = time.monotonic() + timeout / 1000
    while not predicate():
        assert time.monotonic() < deadline, "Timed out waiting for the filesystem model"
        QTest.qWait(10)


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


def test_manual_expansion_survives_lazy_loading_and_search_refresh(qapp, tmp_path):
    nested = _files(tmp_path)
    explorer = QWidget()
    explorer.directory = str(tmp_path)
    explorer.search = QLineEdit(explorer)
    explorer.search_status = QLabel(explorer)
    explorer.searching_text = "Searching"
    explorer.model = QFileSystemModel(explorer)
    explorer.treeView = QTreeView(explorer)
    explorer.treeView.setModel(explorer.model)
    explorer.treeView.setRootIndex(explorer.model.setRootPath(str(tmp_path)))
    search = TreeSearch(explorer)
    explorer.show()
    try:
        explorer.search.setText("project")
        _wait_until(lambda: not search.pending and search.accepted is not None)
        model, tree = explorer.model, explorer.treeView
        for path in [nested.parent, nested]:
            index = model.index(str(path))
            assert index.isValid()
            assert not tree.isExpanded(index), "Descendants should open only on request"
            tree.expand(index)
            _wait_until(lambda: model.rowCount(index) > 0 and not search.pending)
            search.apply()
            assert tree.isExpanded(index)
            child = model.index(0, 0, index)
            assert not tree.isRowHidden(child.row(), index)

        # A new entry triggers another background scan of an already opened tree.
        added = nested / "new.txt"
        added.write_text("new")
        _wait_until(lambda: str(added) in search.accepted and not search.pending)
        assert tree.isExpanded(model.index(str(nested)))
        added_index = model.index(str(added))
        assert not tree.isRowHidden(added_index.row(), added_index.parent())

        unrelated = model.index(str(tmp_path / "unrelated"))
        assert tree.isRowHidden(unrelated.row(), unrelated.parent())
        explorer.search.clear()
        assert not tree.isRowHidden(unrelated.row(), unrelated.parent())
    finally:
        search.cancelled.set()
        search.timer.stop()
        search.apply_timer.stop()
        QThreadPool.globalInstance().waitForDone(5000)
        explorer.close()
        explorer.deleteLater()
        qapp.processEvents()
