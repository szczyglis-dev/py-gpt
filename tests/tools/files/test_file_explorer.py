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
