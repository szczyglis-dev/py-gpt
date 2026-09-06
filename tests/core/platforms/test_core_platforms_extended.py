from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.platforms.platforms as mod
from pygpt_net.core.platforms.platforms import Platforms


def make_platforms(tmp_path):
    config = SimpleNamespace(get_app_path=MagicMock(return_value=str(tmp_path)), is_compiled=MagicMock(return_value=False))
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    return Platforms(window), config


def test_flatpak_detection_uses_environment_or_marker(monkeypatch):
    p = Platforms()
    monkeypatch.setenv("FLATPAK_ID", "io.test.App")
    assert p.is_flatpak() is True
    monkeypatch.delenv("FLATPAK_ID")
    monkeypatch.setattr(mod.os.path, "exists", MagicMock(return_value=False))
    assert p.is_flatpak() is False


def test_ms_store_and_appimage_marker_detection(tmp_path):
    p, _ = make_platforms(tmp_path)
    assert p.is_ms_store() is False and p.is_appimage() is False
    (tmp_path / ".ms_store").write_text("")
    (tmp_path / "data").mkdir(); (tmp_path / "data" / "appimage.conf").write_text("")
    assert p.is_ms_store() is True and p.is_appimage() is True


def test_get_app_type_precedence_and_env_suffix(tmp_path, monkeypatch):
    p, config = make_platforms(tmp_path)
    monkeypatch.setattr(p, "is_flatpak", MagicMock(return_value=True))
    assert p.get_app_type() == "Flatpak"
    assert p.get_env_suffix() == " (Flatpak)"
    monkeypatch.setattr(p, "is_flatpak", MagicMock(return_value=False))
    monkeypatch.setattr(p, "is_snap", MagicMock(return_value=False))
    monkeypatch.setattr(p, "is_appimage", MagicMock(return_value=False))
    config.is_compiled.return_value = False
    assert p.get_app_type() == "source" and p.get_env_suffix() == ""
    config.is_compiled.return_value = True
    monkeypatch.setattr(p, "is_windows", MagicMock(return_value=True))
    monkeypatch.setattr(p, "is_ms_store", MagicMock(return_value=True))
    assert p.get_app_type() == "MS Store"


def test_get_as_string_can_include_or_omit_environment_suffix(tmp_path, monkeypatch):
    p, _ = make_platforms(tmp_path)
    monkeypatch.setattr(p, "get_os", MagicMock(return_value="TestOS"))
    monkeypatch.setattr(p, "get_architecture", MagicMock(return_value="x64"))
    monkeypatch.setattr(p, "get_env_suffix", MagicMock(return_value=" (pkg)"))
    assert p.get_as_string() == "TestOS, x64 (pkg)"
    assert p.get_as_string(env_suffix=False) == "TestOS, x64"


def test_is_svg_supported_handles_validity_and_exceptions(monkeypatch):
    monkeypatch.setattr(mod, "QSvgRenderer", MagicMock(return_value=SimpleNamespace(isValid=lambda: True)))
    assert Platforms().is_svg_supported() is True
    monkeypatch.setattr(mod, "QSvgRenderer", MagicMock(side_effect=RuntimeError("no svg")))
    assert Platforms().is_svg_supported() is False
