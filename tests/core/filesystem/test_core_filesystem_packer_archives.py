import os
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.filesystem.packer import Packer


class FsHelpers:
    @staticmethod
    def common_parent_dir(paths):
        if len(paths) == 1:
            p = Path(paths[0])
            return str(p if p.is_dir() else p.parent)
        return os.path.commonpath([str(Path(p).parent if Path(p).is_file() else Path(p)) for p in paths])

    @staticmethod
    def unique_path(directory, base_name, ext):
        Path(directory).mkdir(parents=True, exist_ok=True)
        candidate = Path(directory) / f"{base_name}{ext}"
        i = 1
        while candidate.exists():
            candidate = Path(directory) / f"{base_name} ({i}){ext}"
            i += 1
        return str(candidate)

    @staticmethod
    def unique_dir(directory, base_name):
        Path(directory).mkdir(parents=True, exist_ok=True)
        candidate = Path(directory) / base_name
        i = 1
        while candidate.exists():
            candidate = Path(directory) / f"{base_name} ({i})"
            i += 1
        return str(candidate)

    @staticmethod
    def strip_archive_name(filename):
        lower = filename.lower()
        for suffix in (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".txz", ".zip", ".tar"):
            if lower.endswith(suffix):
                return filename[:-len(suffix)]
        return os.path.splitext(filename)[0]


def make_packer(tmp_path):
    tmp_dir = tmp_path / "tmp"
    tmp_dir.mkdir()
    debug = SimpleNamespace(log=MagicMock())
    config = SimpleNamespace(get_user_dir=MagicMock(return_value=str(tmp_dir)))
    window = SimpleNamespace(core=SimpleNamespace(config=config, filesystem=FsHelpers(), debug=debug))
    return Packer(window), debug


def test_is_archive_and_can_unpack_use_content_detection(tmp_path):
    packer, _ = make_packer(tmp_path)
    text = tmp_path / "x.txt"
    text.write_text("x")
    archive = tmp_path / "x.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.txt", "A")
    assert packer.is_archive("a.zip") is True
    assert packer.is_archive("a.tar.gz") is True
    assert packer.is_archive("a.txt") is False
    assert packer.can_unpack(str(archive)) is True
    assert packer.can_unpack(str(text)) is False
    assert packer.can_unpack(str(tmp_path / "missing.zip")) is False


def test_pack_paths_zip_preserves_top_level_names_and_empty_directory(tmp_path):
    packer, _ = make_packer(tmp_path)
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "a.txt").write_text("A")
    (folder / "empty").mkdir()
    loose = tmp_path / "b.txt"
    loose.write_text("B")
    out = packer.pack_paths([str(folder), str(loose)], "zip", dest_dir=str(tmp_path), base_name="bundle")
    assert out.endswith("bundle.zip")
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert "folder/a.txt" in names
    assert "folder/empty/" in names
    assert "b.txt" in names


def test_pack_paths_tar_gz_and_default_single_file_name(tmp_path):
    packer, _ = make_packer(tmp_path)
    src = tmp_path / "report.txt"
    src.write_text("hello")
    out = packer.pack_paths([str(src)], "tgz", dest_dir=str(tmp_path))
    assert out.endswith("report.tar.gz")
    with tarfile.open(out, "r:gz") as tf:
        assert "report.txt" in tf.getnames()
    assert packer.pack_paths([], "zip") == ""
    assert packer.pack_paths([str(src)], "rar", dest_dir=str(tmp_path)) == ""


def test_unpack_zip_tar_and_unpack_to_dir(tmp_path):
    packer, _ = make_packer(tmp_path)
    src = tmp_path / "a.txt"
    src.write_text("A")
    zip_path = packer.pack_paths([str(src)], "zip", dest_dir=str(tmp_path), base_name="z")
    tar_path = packer.pack_paths([str(src)], "tar.gz", dest_dir=str(tmp_path), base_name="t")

    zdir = tmp_path / "zout"
    tdir = tmp_path / "tout"
    assert packer.unpack_to_dir(zip_path, str(zdir)) == str(zdir)
    assert (zdir / "a.txt").read_text() == "A"
    assert packer.unpack_to_dir(tar_path, str(tdir)) == str(tdir)
    assert (tdir / "a.txt").read_text() == "A"
    assert packer.unpack_to_dir(str(src), str(tmp_path / "bad")) == ""


def test_unpack_legacy_api_and_remove_tmp(tmp_path):
    packer, _ = make_packer(tmp_path)
    archive = tmp_path / "legacy.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("x.txt", "X")
    out = packer.unpack(str(archive))
    assert Path(out, "x.txt").read_text() == "X"
    packer.remove_tmp(out)
    assert not Path(out).exists()
    packer.remove_tmp(str(tmp_path / "missing"))


def test_unpack_to_sibling_dir_and_collision(tmp_path):
    packer, _ = make_packer(tmp_path)
    archive = tmp_path / "docs.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.txt", "A")
    (tmp_path / "docs").mkdir()
    out = packer.unpack_to_sibling_dir(str(archive))
    assert Path(out).name == "docs (1)"
    assert Path(out, "a.txt").read_text() == "A"
    assert packer.unpack_to_sibling_dir(str(tmp_path / "missing.zip")) == ""


def test_unpack_here_moves_single_top_level_and_cleans_temp(tmp_path):
    packer, _ = make_packer(tmp_path)
    archive = tmp_path / "one.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("folder/a.txt", "A")
    created = packer.unpack_here(str(archive))
    assert len(created) == 1
    assert Path(created[0]).name == "folder"
    assert Path(created[0], "a.txt").read_text() == "A"
    assert packer.unpack_here(str(tmp_path / "not-there.zip")) == []


def test_pack_error_is_logged_and_returns_empty(tmp_path, monkeypatch):
    packer, debug = make_packer(tmp_path)
    src = tmp_path / "a.txt"
    src.write_text("A")
    monkeypatch.setattr(packer, "_pack_zip", MagicMock(side_effect=OSError("boom")))
    assert packer.pack_paths([str(src)], "zip", dest_dir=str(tmp_path), base_name="bad") == ""
    debug.log.assert_called_once()
