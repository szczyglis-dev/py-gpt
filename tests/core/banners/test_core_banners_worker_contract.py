import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import pygpt_net.core.banners.banners as mod
from pygpt_net.core.banners.banners import Banners, BannersWorker


def make_config(tmp_path, values=None):
    values = dict(values or {})
    temp = tmp_path / "tmp"
    temp.mkdir()

    def get(key, default=None):
        return values.get(key, default)

    config = SimpleNamespace(
        data=values,
        get=MagicMock(side_effect=get),
        has=MagicMock(side_effect=lambda key: key in values),
        get_base=MagicMock(return_value=None),
        set=MagicMock(side_effect=lambda key, value: values.__setitem__(key, value)),
        save=MagicMock(),
        get_user_dir=MagicMock(return_value=str(temp)),
    )
    return config, temp, values


def test_banner_config_migration_adds_api_default(tmp_path):
    config, _, values = make_config(tmp_path, {"app_banners_width": 1, "app_banners_height": 2})
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    banners = Banners(window)

    banners._ensure_config()

    assert "app_banners_width" not in values
    assert "app_banners_height" not in values
    assert values["app_banners_api_url"] == Banners.DEFAULT_API_URL
    config.save.assert_called_once_with()


def test_ensure_config_preserves_existing_api_and_skips_save(tmp_path):
    config, _, values = make_config(tmp_path, {"app_banners_api_url": "https://example.test/banners.json"})
    banners = Banners(SimpleNamespace(core=SimpleNamespace(config=config)))
    banners._ensure_config()
    assert values["app_banners_api_url"] == "https://example.test/banners.json"
    config.save.assert_not_called()


def test_run_load_respects_busy_closing_and_starts_worker(tmp_path, monkeypatch):
    config, temp, _ = make_config(tmp_path, {"app_banners_api_url": "https://example.test/b.json"})
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

    ctor.assert_called_once_with(api_url="https://example.test/b.json", user_tmp_path=str(temp))
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
    banners._loading = True
    banners._worker = object()
    banners._handle_finished()
    assert banners._loading is False and banners._worker is None


def make_worker(tmp_path, api="https://example.test/api/banners.json"):
    temp = tmp_path / "tmp"
    temp.mkdir(exist_ok=True)
    return BannersWorker(api, str(temp)), temp


def test_extract_normalize_and_sanitizers(tmp_path):
    worker, _ = make_worker(tmp_path)
    assert worker._extract_items({"items": None}) == []
    assert worker._extract_items({"items": {"a": {"id": "1"}, "b": "bad"}}) == [{"id": "1"}]
    with pytest.raises(ValueError, match="items"):
        worker._extract_items({"items": "bad"})

    item = worker._normalize_item(
        {"id": " x ", "img": "a.png", "tooltip": 7, "url": "javascript:x", "duration": 0},
        0,
    )
    assert item == {"id": "x", "img": "a.png", "tooltip": "7", "url": "", "duration": 1.0}
    assert worker._parse_duration("bad") == worker.DEFAULT_DURATION
    assert worker._parse_duration(999999) == 86400.0
    assert worker._sanitize_click_url("https://example.test/x") == "https://example.test/x"
    assert worker._sanitize_click_url("file:///tmp/x") == ""
    assert worker._safe_id(" ../bad id!! ") == "bad_id"
    assert worker._safe_id("...") == "banner"


def test_image_extension_sniffing_and_url_resolution(tmp_path):
    worker, _ = make_worker(tmp_path)
    assert worker._get_image_extension("x.bin", b"GIF89a...") == ".gif"
    assert worker._get_image_extension("x.bin", b"\x89PNG\r\n\x1a\n") == ".png"
    assert worker._get_image_extension("x.bin", b"\xff\xd8\xff") == ".jpg"
    assert worker._get_image_extension("x.webp", b"") == ".webp"
    assert worker._get_image_extension("x.exe", b"") == ".img"
    assert worker._resolve_remote_image_url("../img/a.png") == "https://example.test/img/a.png"
    with pytest.raises(ValueError):
        worker._resolve_remote_image_url("file:///tmp/x")


def test_cache_manifest_removes_only_plain_filenames(tmp_path):
    worker, temp = make_worker(tmp_path)
    owned = temp / "owned.png"
    owned.write_bytes(b"x")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"y")
    manifest = temp / worker.CACHE_MANIFEST
    manifest.write_text(json.dumps(["owned.png", "../outside.png"]), encoding="utf-8")

    worker._clear_previous_cache(str(temp))

    assert not owned.exists()
    assert outside.exists()
    assert not manifest.exists()


def test_clear_cached_banners_only_removes_manifest_owned_files(tmp_path):
    worker, temp = make_worker(tmp_path)
    owned = temp / "banner.png"
    owned.write_bytes(b"banner")
    unrelated = temp / "interpreter.tmp"
    unrelated.write_bytes(b"keep")
    (temp / worker.CACHE_MANIFEST).write_text(json.dumps([owned.name]), encoding="utf-8")

    worker._clear_cached_banners()

    assert not owned.exists()
    assert unrelated.exists()
    assert not (temp / worker.CACHE_MANIFEST).exists()


def test_load_remote_downloads_images_and_writes_manifest(tmp_path, monkeypatch):
    worker, temp = make_worker(tmp_path)
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


def test_worker_run_reports_remote_error_and_clears_cache(tmp_path, monkeypatch):
    worker, _ = make_worker(tmp_path)
    monkeypatch.setattr(worker, "_load_remote", MagicMock(side_effect=RuntimeError("network")))
    clear_cached = MagicMock()
    monkeypatch.setattr(worker, "_clear_cached_banners", clear_cached)
    loaded = []
    finished = []
    worker.signals.loaded.connect(lambda result: loaded.append(result))
    worker.signals.finished.connect(lambda: finished.append(True))

    worker.run()

    clear_cached.assert_called_once_with()
    assert loaded == [{"items": [], "source": "remote", "error": "network"}]
    assert finished == [True]
