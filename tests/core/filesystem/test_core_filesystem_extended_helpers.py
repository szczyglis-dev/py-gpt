import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.filesystem.filesystem import Filesystem


def make_fs(tmp_path):
    user = tmp_path / "user"
    data = user / "data"
    upload = user / "upload"
    data.mkdir(parents=True)
    upload.mkdir()
    dirs = {"data": "data", "upload": "upload", "img": "img", "capture": "capture", "tmp": "tmp"}
    config = SimpleNamespace(
        path=str(user),
        dirs=dirs,
        get_user_path=MagicMock(return_value=str(user)),
        has=MagicMock(return_value=False),
        get=MagicMock(return_value=False),
        get_user_dir=MagicMock(side_effect=lambda key: str({"data": data, "upload": upload}.get(key, user / key))),
        get_app_path=MagicMock(return_value=str(tmp_path / "app")),
    )
    platforms = SimpleNamespace(is_windows=MagicMock(return_value=False))
    window = SimpleNamespace(core=SimpleNamespace(config=config, platforms=platforms))
    return Filesystem(window), user, data, upload


def test_make_local_list_img_and_workdir_membership(tmp_path):
    fs, user, data, _ = make_fs(tmp_path)
    image = str(data / "a.png")
    assert fs.make_local_list_img([image, str(data / "x.txt")]) == [fs.make_local(image)]
    assert fs.in_work_dir(image) is True
    assert fs.in_work_dir(str(tmp_path / "outside.png")) is False


def test_store_upload_and_remove_upload_handle_name_collisions(tmp_path):
    fs, _, _, upload = make_fs(tmp_path)
    src = tmp_path / "same.txt"
    src.write_text("first")
    first = fs.store_upload(str(src))
    assert Path(first).read_text() == "first"
    src.write_text("second")
    second = fs.store_upload(str(src))
    assert second != first
    assert Path(second).read_text() == "second"
    fs.remove_upload(second)
    assert not Path(second).exists()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep")
    fs.remove_upload(str(outside))
    assert outside.exists()


def test_size_helpers_use_bytes_and_human_readable_formats(tmp_path):
    fs, user, data, _ = make_fs(tmp_path)
    (data / "a.bin").write_bytes(b"1234")
    (data / "b.bin").write_bytes(b"12")
    assert fs.get_directory_size(str(data), human_readable=False) == 6
    assert fs.get_datadir_size(str(user), human_readable=False) == 6
    assert fs.get_directory_size(str(tmp_path / "missing"), human_readable=False) == 0
    assert fs.sizeof_fmt(1024) == "1,0 KB"
    assert fs.sizeof_fmt("bad") == "-"

    (user / "db.sqlite").write_bytes(b"123")
    (user / "db.sqlite.backup").write_bytes(b"45")
    assert fs.get_db_size(str(user), human_readable=False) == 5


def test_directory_helpers_and_unique_names(tmp_path):
    fs, user, data, _ = make_fs(tmp_path)
    assert fs.is_directory_empty(str(data)) is True
    nested = data / "nested"
    nested.mkdir()
    (data / "root.txt").write_text("r")
    (nested / "child.txt").write_text("c")
    assert fs.is_directory_empty(str(data)) is False
    assert set(fs.get_files_from_dir(str(data), recursive=False)) == {str(data / "root.txt")}
    assert set(fs.get_files_from_dir(str(data), recursive=True)) == {str(data / "root.txt"), str(nested / "child.txt")}
    assert fs.get_files_from_dir(str(tmp_path / "missing")) == []

    assert fs.common_parent_dir([]) == str(user)
    assert fs.common_parent_dir([str(data / "root.txt")]) == str(data)
    assert fs.common_parent_dir([str(data / "root.txt"), str(nested / "child.txt")]) == str(data)

    p1 = Path(fs.unique_path(str(data), "name", ".txt"))
    assert p1.name == "name.txt"
    p1.write_text("x")
    assert Path(fs.unique_path(str(data), "name", ".txt")).name == "name (1).txt"
    d1 = Path(fs.unique_dir(str(data), "folder"))
    d1.mkdir()
    assert Path(fs.unique_dir(str(data), "folder")).name == "folder (1)"


def test_workdir_detection_and_archive_name_stripping(tmp_path):
    fs, user, _, _ = make_fs(tmp_path)
    assert fs.is_workdir_in_path(str(user)) is False
    (user / "config.json").write_text("{}")
    (user / "db.sqlite").write_bytes(b"")
    assert fs.is_workdir_in_path(str(user)) is True
    assert fs.strip_archive_name("backup.tar.gz") == "backup"
    assert fs.strip_archive_name("backup.TGZ") == "backup"
    assert fs.strip_archive_name("backup.zip") == "backup"
    assert fs.strip_archive_name("notes.txt") == "notes"


def test_copy_and_clear_workdir_respect_exclusions(tmp_path):
    fs, _, _, _ = make_fs(tmp_path)
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir(); dst.mkdir()
    (src / "db.sqlite").write_text("db")
    (src / "keep.txt").write_text("keep")
    (src / "profile.json").write_text("profile")
    (src / "data").mkdir(); (src / "data" / "x.txt").write_text("x")
    assert fs.copy_workdir(str(src), str(dst), copy_db=False, copy_datadir=False) is True
    assert (dst / "keep.txt").exists()
    assert not (dst / "db.sqlite").exists()
    assert not (dst / "data").exists()
    assert (dst / "path.cfg").exists()
    assert not (dst / "profile.json").exists()

    (dst / "app.log").write_text("log")
    (dst / "profile.json").write_text("profile")
    (dst / "db.sqlite").write_text("db")
    (dst / "data").mkdir(); (dst / "data" / "x").write_text("x")
    (dst / "remove.me").write_text("bye")
    assert fs.clear_workdir(str(dst), remove_db=False, remove_datadir=False) is True
    assert (dst / "app.log").exists()
    assert (dst / "profile.json").exists()
    assert (dst / "db.sqlite").exists()
    assert (dst / "data").exists()
    assert not (dst / "remove.me").exists()


def test_free_disk_space_can_return_raw_integer(tmp_path):
    fs, *_ = make_fs(tmp_path)
    free = fs.get_free_disk_space(str(tmp_path / "file"), human_readable=False)
    assert isinstance(free, int)
    assert free >= 0
