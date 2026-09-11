import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.filesystem.parser import Parser
from pygpt_net.core.filesystem.types import Types


def test_types_recognize_media_case_insensitively_and_expose_extensions():
    types = Types()
    assert types.is_image("photo.JPEG") is True
    assert types.is_video("clip.MP4") is True
    assert types.is_audio("sound.FLAC") is True
    assert types.is_image("notes.txt") is False
    assert ".webp" in types.get_img_ext()
    assert ".webm" in types.get_video_ext()
    assert ".wav" in types.get_audio_ext()


def test_excluded_extensions_are_sorted_and_cover_binary_archives_media():
    excluded = Types().get_excluded_extensions()
    assert excluded == sorted(excluded)
    for ext in ("png", "mp3", "mp4", "zip", "exe", "whl"):
        assert ext in excluded


def make_parser(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    def is_in(path, root):
        try:
            return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
        except ValueError:
            return False

    filesystem = SimpleNamespace(
        get_data_dir=MagicMock(return_value=str(data_dir)),
        get_shared_data_dir=MagicMock(return_value=str(data_dir)),
        _is_path_in=MagicMock(side_effect=is_in),
        is_global_profile_path=MagicMock(return_value=False),
        make_local_list=MagicMock(side_effect=lambda paths, ctx=None: [f"local:{p}" for p in paths]),
    )
    config = SimpleNamespace(get_user_dir=MagicMock(return_value=str(data_dir)))
    window = SimpleNamespace(core=SimpleNamespace(config=config, filesystem=filesystem))
    return Parser(window), filesystem, data_dir


def test_extract_data_paths_handles_posix_windows_quotes_and_deduplicates(tmp_path):
    parser, _, _ = make_parser(tmp_path)
    text = (
        'saved "/home/user/data/a file.png" and /home/user/data/b.txt; '
        "also 'C:\\work\\DATA\\c.jpg' and /home/user/data/b.txt"
    )
    paths = parser.extract_data_paths(text)
    assert "/home/user/data/a file.png" in paths
    assert "/home/user/data/b.txt" in paths
    assert r"C:\work\DATA\c.jpg" in paths
    assert paths.count("/home/user/data/b.txt") == 1
    assert parser.extract_data_paths("") == []


def test_extract_data_paths_ignores_non_data_paths(tmp_path):
    parser, _, _ = make_parser(tmp_path)
    assert parser.extract_data_paths("/home/user/files/a.txt /tmp/cache/x.png") == []


def test_extract_data_files_rebases_to_local_data_and_collects_images(tmp_path):
    parser, filesystem, data_dir = make_parser(tmp_path)
    ctx = SimpleNamespace(files=[], images=[])
    response = "/sandbox/data/sub/a.png /sandbox/data/sub/readme.txt /sandbox/data/sub/a.png"
    paths = parser.extract_data_files(ctx, response)
    expected = [str(data_dir / "sub" / "a.png"), str(data_dir / "sub" / "readme.txt")]
    assert paths == expected
    assert ctx.files == expected
    assert ctx.images == [f"local:{expected[0]}"]
    filesystem.make_local_list.assert_called_once_with([expected[0]], ctx=ctx)


def test_extract_data_files_none_response_is_noop(tmp_path):
    parser, filesystem, _ = make_parser(tmp_path)
    ctx = SimpleNamespace(files=["old"], images=["old"])
    assert parser.extract_data_files(ctx, None) == []
    filesystem.make_local_list.assert_not_called()
