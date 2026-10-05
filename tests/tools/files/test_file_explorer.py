from pygpt_net.tools.files.core.clipboard import Clipboard
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.files.ui.drop import ExplorerDropHandler
from pygpt_net.tools.files.ui.explorer import FileExplorer
from pygpt_net.tools.files.ui.tree import MultiDragTreeView


class _Url:
    def __init__(self, path, local=True):
        self.path = path
        self.local = local

    def isLocalFile(self):
        return self.local

    def toLocalFile(self):
        return self.path

    def toString(self, *_):
        return "file://" + self.path


class _Mime:
    def __init__(self, urls):
        self._urls = urls

    def hasUrls(self):
        return bool(self._urls)

    def urls(self):
        return self._urls


def test_multidrag_selected_count_handles_errors():
    widget = SimpleNamespace(selectionModel=lambda: MagicMock(selectedRows=lambda *_: [1, 2, 3]))
    assert MultiDragTreeView._selected_count(widget) == 3

    widget = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError("gone")))
    assert MultiDragTreeView._selected_count(widget) == 0


def test_multidrag_builds_unique_local_urls():
    model = MagicMock()
    model.filePath.side_effect = ["/a", "/a", "/b"]
    selection = MagicMock()
    selection.selectedRows.return_value = [MagicMock(), MagicMock(), MagicMock()]
    widget = SimpleNamespace(model=lambda: model, selectionModel=lambda: selection)

    with patch("pygpt_net.tools.files.ui.tree.QUrl.fromLocalFile", side_effect=lambda p: p, create=True):
        assert MultiDragTreeView._make_urls_from_selection(widget) == ["/a", "/b"]


def test_drop_handler_extracts_only_local_paths():
    handler = SimpleNamespace()
    md = _Mime([_Url("/tmp/a"), _Url("https://example", local=False), _Url("/tmp/b")])

    assert ExplorerDropHandler._mime_has_local_urls(handler, md) is True
    assert ExplorerDropHandler._local_paths_from_mime(handler, md) == ["/tmp/a", "/tmp/b"]
    assert ExplorerDropHandler._mime_has_local_urls(handler, _Mime([])) is False


def test_drop_handler_target_directory_uses_context_and_root(tmp_path):
    root = str(tmp_path)
    directory = tmp_path / "dir"
    directory.mkdir()
    idx = MagicMock()
    idx.isValid.return_value = True
    parent = MagicMock()
    parent.isValid.return_value = True
    model = MagicMock()
    model.filePath.side_effect = lambda value: str(directory) if value is idx else root
    handler = SimpleNamespace(explorer=SimpleNamespace(model=model, directory=root))

    assert ExplorerDropHandler._target_dir_from_context(handler, {"type": "into_dir", "idx": idx}) == str(directory)
    assert ExplorerDropHandler._target_dir_from_context(handler, {"type": "into_parent", "parent_idx": parent}) == root
    assert ExplorerDropHandler._target_dir_from_context(handler, {"type": "empty"}) == root


def test_selected_paths_are_unique_and_ignore_bad_indexes():
    indexes = [MagicMock(), MagicMock(), MagicMock()]
    selection = MagicMock(selectedRows=MagicMock(return_value=indexes))
    model = MagicMock()
    model.filePath.side_effect = ["/a", "/a", "/b"]
    explorer = SimpleNamespace(treeView=SimpleNamespace(selectionModel=lambda: selection), model=model)

    assert FileExplorer.selected_paths(explorer) == ["/a", "/b"]


def test_parent_for_selection_single_file_and_directory(tmp_path):
    folder = tmp_path / "folder"
    folder.mkdir()
    file = folder / "file.txt"
    file.write_text("x")
    explorer = SimpleNamespace(directory=str(tmp_path))

    assert FileExplorer.parent_for_selection(explorer, []) == str(tmp_path)
    assert FileExplorer.parent_for_selection(explorer, [str(folder)]) == str(folder)
    assert FileExplorer.parent_for_selection(explorer, [str(file)]) == str(folder)


def test_copy_paths_copies_files_and_generates_unique_name(tmp_path):
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()
    source = src_dir / "item.txt"
    source.write_text("payload")
    (dst_dir / "item.txt").write_text("old")

    explorer = SimpleNamespace(window=SimpleNamespace(core=SimpleNamespace(debug=MagicMock())))
    copied = Clipboard(explorer).copy_paths([str(source)], str(dst_dir))

    assert len(copied) == 1
    assert os.path.basename(copied[0]) == "item - Copy.txt"
    assert (dst_dir / "item - Copy.txt").read_text() == "payload"


def test_move_paths_refuses_moving_directory_into_itself(tmp_path):
    src = tmp_path / "src"
    child = src / "child"
    child.mkdir(parents=True)
    explorer = SimpleNamespace(window=SimpleNamespace(core=SimpleNamespace(debug=MagicMock())))

    moved = Clipboard(explorer).move_paths([str(src)], str(child))

    assert moved == []
    assert src.exists()


def test_unique_dest_uses_copy_suffixes(tmp_path):
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "a - Copy.txt").write_text("2")
    explorer = SimpleNamespace()

    assert Clipboard(explorer).unique_dest(str(tmp_path), "new.txt") == str(tmp_path / "new.txt")
    assert Clipboard(explorer).unique_dest(str(tmp_path), "a.txt") == str(tmp_path / "a - Copy (2).txt")


def test_clipboard_payload_helpers_use_expected_line_endings():
    urls = [_Url("/a"), _Url("/b")]
    explorer = SimpleNamespace()

    assert Clipboard(explorer).uri_list(urls) == b"file:///a\r\nfile:///b\r\n"
    assert Clipboard(explorer).gnome_payload(urls, "cut") == b"cut\nfile:///a\nfile:///b\n"


def test_get_clipboard_falls_back_to_internal_buffer():
    buffer = Clipboard(SimpleNamespace())
    buffer.paths = ["/internal/a"]
    buffer.mode = "cut"
    clipboard = MagicMock()
    clipboard.mimeData.return_value = None

    with patch("pygpt_net.tools.files.core.clipboard.QGuiApplication.clipboard", return_value=clipboard, create=True):
        paths, mode = buffer.files()

    assert paths == ["/internal/a"]
    assert mode == "cut"


def _columns_explorer(ratio=0.45, swapped=False):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSplitter, QWidget

    splitter = QSplitter(Qt.Horizontal)
    files = QWidget()
    files.setMinimumWidth(220)
    preview = QWidget()
    splitter.addWidget(files)
    splitter.addWidget(preview)
    splitter.resize(1000, 300)
    splitter.show()
    explorer = SimpleNamespace(
        splitter=splitter, files_panel=files, preview=preview,
        columns_swapped=swapped, _files_ratio=ratio, _closed=False,
        _columns_resize_timer=MagicMock(),
        footer_layout=MagicMock(),
        window=SimpleNamespace(core=SimpleNamespace(config=MagicMock())),
    )
    FileExplorer._apply_columns_layout(explorer, swapped)
    FileExplorer._resize_columns(explorer)
    return explorer


def test_columns_follow_user_ratio_after_resize_collapse_and_swap():
    explorer = _columns_explorer()
    splitter = explorer.splitter
    try:
        assert abs(splitter.sizes()[0] / sum(splitter.sizes()) - 0.45) < 0.002
        splitter.setSizes([650, 350])
        FileExplorer._remember_columns_ratio(explorer)
        preferred = explorer._files_ratio
        for width in (1600, 600, 1200):
            splitter.resize(width, 300)
            FileExplorer._resize_columns(explorer)
            assert abs(splitter.sizes()[0] / sum(splitter.sizes()) - preferred) < 0.003
        splitter.hide()
        splitter.resize(300, 300)
        FileExplorer._resize_columns(explorer)
        splitter.resize(1400, 300)
        splitter.show()
        FileExplorer._resize_columns(explorer)
        assert abs(splitter.sizes()[0] / sum(splitter.sizes()) - preferred) < 0.003
        FileExplorer._apply_columns_layout(explorer, True)
        FileExplorer._resize_columns(explorer)
        assert abs(splitter.sizes()[1] / sum(splitter.sizes()) - preferred) < 0.003
        assert explorer._files_ratio == preferred
        explorer.window.core.config.set.assert_called_with('files.columns.ratio', preferred)
    finally:
        splitter.close()


def test_columns_minimum_width_does_not_replace_preferred_ratio():
    explorer = _columns_explorer(ratio=0.3)
    try:
        explorer.splitter.resize(400, 300)
        FileExplorer._resize_columns(explorer)
        assert explorer.splitter.sizes()[0] >= 220
        explorer.splitter.resize(1200, 300)
        FileExplorer._resize_columns(explorer)
        assert abs(explorer.splitter.sizes()[0] / sum(explorer.splitter.sizes()) - 0.3) < 0.002
        assert explorer._files_ratio == 0.3
    finally:
        explorer.splitter.close()


def test_columns_ratio_loads_saved_value_and_rejects_invalid_values():
    config = MagicMock()
    explorer = SimpleNamespace(window=SimpleNamespace(core=SimpleNamespace(config=config)))
    for value in (None, 'bad', 0, 1, -1, float('nan')):
        config.get.return_value = value
        assert FileExplorer._load_columns_ratio(explorer) == 0.45
    config.get.return_value = 0.62
    assert FileExplorer._load_columns_ratio(explorer) == 0.62
