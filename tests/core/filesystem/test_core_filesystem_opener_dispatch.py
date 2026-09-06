from pathlib import Path
from unittest.mock import MagicMock

import pygpt_net.core.filesystem.opener as mod
from pygpt_net.core.filesystem.opener import Opener


def test_open_path_dispatches_windows_file_and_reveal(tmp_path, monkeypatch):
    file = tmp_path / "a.txt"; file.write_text("x")
    monkeypatch.setattr(mod, "IS_WINDOWS", True)
    monkeypatch.setattr(mod, "IS_MAC", False)
    monkeypatch.setattr(Opener, "_open_file_windows", MagicMock(return_value=True))
    monkeypatch.setattr(Opener, "_reveal_windows", MagicMock(return_value=True))
    assert Opener.open_path(str(file)) is True
    Opener._open_file_windows.assert_called_once_with(str(file.resolve()))
    assert Opener.open_path(str(file), reveal=True) is True
    Opener._reveal_windows.assert_called_once_with(str(file.resolve()))


def test_open_path_dispatches_macos_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_WINDOWS", False)
    monkeypatch.setattr(mod, "IS_MAC", True)
    monkeypatch.setattr(Opener, "_open_dir_mac", MagicMock(return_value=True))
    assert Opener.open_path(str(tmp_path)) is True
    Opener._open_dir_mac.assert_called_once_with(str(tmp_path.resolve()))


def test_open_path_linux_reveal_falls_back_to_parent(tmp_path, monkeypatch):
    file = tmp_path / "a.txt"; file.write_text("x")
    monkeypatch.setattr(mod, "IS_WINDOWS", False)
    monkeypatch.setattr(mod, "IS_MAC", False)
    monkeypatch.setattr(Opener, "_reveal_linux", MagicMock(return_value=False))
    monkeypatch.setattr(Opener, "_open_dir_linux", MagicMock(return_value=True))
    assert Opener.open_path(str(file), reveal=True) is True
    Opener._open_dir_linux.assert_called_once_with(str(tmp_path.resolve()))
