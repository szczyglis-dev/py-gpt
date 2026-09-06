import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import pygpt_net.core.banners.banners as mod
from pygpt_net.core.banners.banners import Banners, BannersWorker


def make_config(tmp_path, values=None):
    values = dict(values or {})
    app = tmp_path / "app"
    temp = tmp_path / "tmp"
    app.mkdir(); temp.mkdir()

    def get(key, default=None):
        return values.get(key, default)

    config = SimpleNamespace(
        data=values,
        get=MagicMock(side_effect=get),
        has=MagicMock(side_effect=lambda key: key in values),
        get_base=MagicMock(return_value=None),
        set=MagicMock(side_effect=lambda key, value: values.__setitem__(key, value)),
        save=MagicMock(),
        get_app_path=MagicMock(return_value=str(app)),
        get_user_dir=MagicMock(return_value=str(temp)),
    )
    return config, app, temp, values


def test_banner_default_path_and_config_migration(tmp_path):
    config, app, _, values = make_config(tmp_path, {"app_banners_width": 1, "app_banners_height": 2})
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    banners = Banners(window)
    assert banners.get_default_path() == str(app / "data" / "default.png")
    banners._ensure_config()
    assert "app_banners_width" not in values
    assert "app_banners_height" not in values
    assert values["app_banners_api_url"] == Banners.DEFAULT_API_URL
    config.save.assert_called_once_with()


def test_ensure_config_preserves_existing_api_and_skips_save(tmp_path):
    config, _, _, values = make_config(tmp_path, {"app_banners_api_url": "https://example.test/banners.json"})
    banners = Banners(SimpleNamespace(core=SimpleNamespace(config=config)))
    banners._ensure_config()
    assert values["app_banners_api_url"] == "https://example.test/banners.json"
    config.save.assert_not_called()


def test_run_load_respects_busy_closing_and_starts_worker(tmp_path, monkeypatch):
    config, app, temp, values = make_config(tmp_path, {"app_banners_api_url": "https://example.test/b.json"})
    threadpool = SimpleNamespace(start=MagicMock())
    window = SimpleNamespace(core=SimpleNamespace(config=config), is_closing=False, threadpool=threadpool)
    banners = Banners(window)
    fake_worker = SimpleNamespace(
        signals=SimpleNamespace(
            loaded=SimpleNamespace(connect=MagicMock()),
            finished=SimpleNamespace(connect=MagicMock()),
        )
    )
    ctor = MagicMock(return_value=fake_worker)
    monkeypatch.setattr(mod, "BannersWorker", ctor)
    banners.run_load()
    ctor.assert_called_once_with(api_url="https://example.test/b.json", app_path=str(app), user_tmp_path=str(temp))
    threadpool.start.assert_called_once_with(fake_worker)
    assert banners._loading is True and banners._worker is fake_worker

    threadpool.start.reset_mock()
    banners.run_load()
    threadpool.start.assert_not_called()
    banners._handle_finished()
    window.is_closing = True
    banners.run_load()
    threadpool.start.assert_not_called()


def test_handle_loaded_emits_items_and_finished_resets_state(tmp_path):
    config, *_ = make_config(tmp_path)
    banners = Banners(SimpleNamespace(core=SimpleNamespace(config=config)))
    emitted = []
    banners.loaded.connect(lambda items: emitted.append(items))
    banners._handle_loaded({"items": [{"id": "a"}], "source": "remote", "error": None})
    assert emitted == [[{"id": "a"}]]
    banners._loading = True; banners._worker = object()
    banners._handle_finished()
    assert banners._loading is False and banners._worker is None


def make_worker(tmp_path, api="https://example.test/api/banners.json"):
    app = tmp_path / "app"; temp = tmp_path / "tmp"
    app.mkdir(exist_ok=True); temp.mkdir(exist_ok=True)
    return BannersWorker(api, str(app), str(temp)), app, temp


def test_extract_normalize_and_sanitizers(tmp_path):
    worker, *_ = make_worker(tmp_path)
    assert worker._extract_items({"items": None}) == []
    assert worker._extract_items({"items": {"a": {"id": "1"}, "b": "bad"}}) == [{"id": "1"}]
    with pytest.raises(ValueError, match="items"):
        worker._extract_items({"items": "bad"})

    item = worker._normalize_item({"id": " x ", "img": "a.png", "tooltip": 7, "url": "javascript:x", "duration": 0}, 0)
    assert item == {"id": "x", "img": "a.png", "tooltip": "7", "url": "", "duration": 1.0}
    assert worker._parse_duration("bad") == worker.DEFAULT_DURATION
    assert worker._parse_duration(999999) == 86400.0
    assert worker._sanitize_click_url("https://example.test/x") == "https://example.test/x"
    assert worker._sanitize_click_url("file:///tmp/x") == ""
    assert worker._safe_id(" ../bad id!! ") == "bad_id"
    assert worker._safe_id("...") == "banner"


def test_image_extension_sniffing_and_url_resolution(tmp_path):
    worker, *_ = make_worker(tmp_path)
    assert worker._get_image_extension("x.bin", b"GIF89a...") == ".gif"
    assert worker._get_image_extension("x.bin", b"\x89PNG\r\n\x1a\n") == ".png"
    assert worker._get_image_extension("x.bin", b"\xff\xd8\xff") == ".jpg"
    assert worker._get_image_extension("x.webp", b"") == ".webp"
    assert worker._get_image_extension("x.exe", b"") == ".img"
    assert worker._resolve_remote_image_url("../img/a.png") == "https://example.test/img/a.png"
    with pytest.raises(ValueError):
        worker._resolve_remote_image_url("file:///tmp/x")


def test_local_load_constrains_image_to_bundled_directory(tmp_path):
    worker, app, _ = make_worker(tmp_path)
    data = app / "data"; banner_dir = data / "banners"
    banner_dir.mkdir(parents=True)
    (banner_dir / "ok.png").write_bytes(b"x")
    (data / "outside.png").write_bytes(b"outside")
    (data / "banners.json").write_text(json.dumps({"items": [
        {"id": "ok", "img": "ok.png"},
        {"id": "traversal", "img": "../outside.png"},
    ]}), encoding="utf-8")
    items = worker._load_local()
    assert items[0]["path"] == str(banner_dir / "ok.png")
    assert items[1]["path"] is None


def test_cache_manifest_removes_only_plain_filenames(tmp_path):
    worker, _, temp = make_worker(tmp_path)
    owned = temp / "owned.png"; owned.write_bytes(b"x")
    outside = tmp_path / "outside.png"; outside.write_bytes(b"y")
    manifest = temp / worker.CACHE_MANIFEST
    manifest.write_text(json.dumps(["owned.png", "../outside.png"]), encoding="utf-8")
    worker._clear_previous_cache(str(temp))
    assert not owned.exists()
    assert outside.exists()
    assert not manifest.exists()


def test_load_remote_downloads_images_and_writes_manifest(tmp_path, monkeypatch):
    worker, _, temp = make_worker(tmp_path)
    monkeypatch.setattr(worker, "_fetch_json", MagicMock(return_value={"items": [
        {"id": "Hello world", "img": "img.png", "url": "https://example.test"},
        {"id": "text-only", "img": ""},
    ]}))
    monkeypatch.setattr(worker, "_fetch_bytes", MagicMock(return_value=b"\x89PNG\r\n\x1a\nDATA"))
    items = worker._load_remote()
    assert len(items) == 2
    image_path = Path(items[0]["path"])
    assert image_path.exists() and image_path.parent == temp
    assert image_path.name.startswith("Hello_world_") and image_path.suffix == ".png"
    assert items[1]["path"] is None
    manifest = json.loads((temp / worker.CACHE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest == [image_path.name]


def test_worker_run_falls_back_to_local_on_remote_error(tmp_path, monkeypatch):
    worker, *_ = make_worker(tmp_path)
    monkeypatch.setattr(worker, "_load_remote", MagicMock(side_effect=RuntimeError("network")))
    monkeypatch.setattr(worker, "_load_local", MagicMock(return_value=[{"id": "local"}]))
    loaded = []; finished = []
    worker.signals.loaded.connect(lambda result: loaded.append(result))
    worker.signals.finished.connect(lambda: finished.append(True))
    worker.run()
    assert loaded == [{"items": [{"id": "local"}], "source": "bundled", "error": "network"}]
    assert finished == [True]
