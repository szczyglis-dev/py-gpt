import os
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.plugin.cmd_files import Plugin
from pygpt_net.plugin.cmd_files.worker import Worker
from tests.mocks import mock_window


def _worker(mock_window, tmp_path):
    plugin = Plugin(window=mock_window)
    plugin.setup()
    mock_window.core.config.get_user_dir = MagicMock(return_value=str(tmp_path))
    mock_window.core.filesystem.get_data_dir = MagicMock(return_value=str(tmp_path))
    worker = Worker()
    worker.from_defaults(plugin)
    worker.log = MagicMock()
    return plugin, worker


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a.zip", ("zip", "w")),
        ("a.tar", ("tar", "w")),
        ("a.tar.gz", ("tar", "w:gz")),
        ("a.tgz", ("tar", "w:gz")),
        ("a.tar.bz2", ("tar", "w:bz2")),
        ("a.tbz2", ("tar", "w:bz2")),
        ("a.tar.xz", ("tar", "w:xz")),
        ("a.txz", ("tar", "w:xz")),
    ],
)
def test_archive_format(name, expected):
    assert Worker._archive_format(name) == expected


def test_archive_format_rejects_unknown_extension():
    with pytest.raises(ValueError, match="Unsupported archive format"):
        Worker._archive_format("archive.rar")


def test_archive_sources_normalizes_values_and_rejects_empty():
    assert Worker._archive_sources("a") == ["a"]
    assert Worker._archive_sources(("a", "", None, "b")) == ["a", "b"]
    with pytest.raises(ValueError, match="Source path"):
        Worker._archive_sources([])


def test_archive_member_target_accepts_child_and_rejects_traversal(tmp_path):
    expected = os.path.realpath(tmp_path / "dir" / "file.txt")
    assert Worker._archive_member_target(str(tmp_path), "dir/file.txt") == expected
    for unsafe in ("../escape.txt", "/absolute.txt", "dir/../../escape.txt", ""):
        with pytest.raises(ValueError, match="Unsafe archive member"):
            Worker._archive_member_target(str(tmp_path), unsafe)


def test_human_readable_size_and_prepare_path(mock_window, tmp_path):
    _, worker = _worker(mock_window, tmp_path)
    assert worker.get_human_readable_size(0) == "0.00 B"
    assert worker.get_human_readable_size(1536) == "1.50 KB"
    assert worker.prepare_path(".") == str(tmp_path)
    assert worker.prepare_path("file.txt") == str(tmp_path / "file.txt")
    absolute = str(tmp_path / "absolute.txt")
    assert worker.prepare_path(absolute) == absolute


def test_zip_unpack_rejects_path_traversal(mock_window, tmp_path):
    _, worker = _worker(mock_window, tmp_path)
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "bad")

    with pytest.raises(ValueError, match="Unsafe archive member"):
        worker._unpack_zip(str(archive), str(tmp_path / "out"))
    assert not (tmp_path.parent / "escape.txt").exists()


def test_tar_unpack_rejects_link_member(mock_window, tmp_path):
    _, worker = _worker(mock_window, tmp_path)
    archive = tmp_path / "unsafe.tar"
    info = tarfile.TarInfo("link")
    info.type = tarfile.SYMTYPE
    info.linkname = "target"
    with tarfile.open(archive, "w") as tf:
        tf.addfile(info)

    with pytest.raises(ValueError, match="archive link"):
        worker._unpack_tar(str(archive), str(tmp_path / "out"))


def test_pack_and_unpack_zip_roundtrip(mock_window, tmp_path):
    _, worker = _worker(mock_window, tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "one.txt").write_text("one", encoding="utf-8")
    nested = src / "nested"
    nested.mkdir()
    (nested / "two.txt").write_text("two", encoding="utf-8")

    pack_item = {"cmd": "pack_archive", "params": {"src": "src", "dst": "bundle.zip"}}
    packed = worker.cmd_pack_archive(pack_item)
    assert packed["result"]["result"] == "OK"
    assert packed["result"]["format"] == "zip"
    assert (tmp_path / "bundle.zip").is_file()

    unpack_item = {"cmd": "unpack_archive", "params": {"src": "bundle.zip", "dst": "unpacked"}}
    unpacked = worker.cmd_unpack_archive(unpack_item)
    assert unpacked["result"]["result"] == "OK"
    assert unpacked["result"]["format"] == "zip"
    assert (tmp_path / "unpacked" / "src" / "one.txt").read_text(encoding="utf-8") == "one"
    assert (tmp_path / "unpacked" / "src" / "nested" / "two.txt").read_text(encoding="utf-8") == "two"


def test_zip_add_path_skips_symlink_when_supported(mock_window, tmp_path):
    _, worker = _worker(mock_window, tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    (src / "normal.txt").write_text("ok", encoding="utf-8")
    link = src / "link.txt"
    try:
        link.symlink_to(src / "normal.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")

    archive_path = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        worker._zip_add_path(archive, str(src))
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
    assert any(name.endswith("normal.txt") for name in names)
    assert not any(name.endswith("link.txt") for name in names)
