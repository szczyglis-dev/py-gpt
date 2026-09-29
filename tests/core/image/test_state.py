#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.image.state as state


def make_core():
    filesystem = MagicMock()
    filesystem.normalize_local_path.side_effect = lambda path, ctx=None: str(path)
    filesystem.to_workdir.side_effect = lambda path, auto_prefix=False, ctx=None: str(path)
    filesystem.make_local.side_effect = lambda path, ctx=None: f"local:{path}"
    filesystem.types.is_image.side_effect = lambda path: str(path).lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    return SimpleNamespace(
        filesystem=filesystem,
        ctx=MagicMock(),
        attachments=MagicMock(),
    )


def make_ctx(extra=None, images=None):
    return SimpleNamespace(
        extra={} if extra is None else extra,
        images=[] if images is None else images,
    )


def test_resolve_local_image_path_rejects_empty_remote_missing_and_non_image(tmp_path):
    core = make_core()
    image = tmp_path / "image.png"
    text = tmp_path / "note.txt"
    image.write_bytes(b"x")
    text.write_text("x", encoding="utf-8")

    assert state.resolve_local_image_path(core, None) is None
    assert state.resolve_local_image_path(core, "https://example.com/a.png") is None
    assert state.resolve_local_image_path(core, str(tmp_path / "missing.png")) is None
    assert state.resolve_local_image_path(core, str(text)) is None
    assert state.resolve_local_image_path(core, str(image)) == str(image)


def test_resolve_local_image_path_falls_back_to_workdir_conversion(tmp_path):
    core = make_core()
    image = tmp_path / "image.png"
    image.write_bytes(b"x")
    core.filesystem.normalize_local_path.side_effect = RuntimeError("normalize")
    core.filesystem.to_workdir.side_effect = None
    core.filesystem.to_workdir.return_value = str(image)

    assert state.resolve_local_image_path(core, "%workdir%/data/image.png") == str(image)
    core.filesystem.to_workdir.assert_called_once_with(
        "%workdir%/data/image.png", auto_prefix=False, ctx=None,
    )


def test_resolve_local_image_path_returns_none_when_both_resolvers_fail():
    core = make_core()
    core.filesystem.normalize_local_path.side_effect = RuntimeError("normalize")
    core.filesystem.to_workdir.side_effect = RuntimeError("workdir")

    assert state.resolve_local_image_path(core, "image.png") is None


def test_make_portable_image_path_requires_existing_image_and_uses_make_local(tmp_path):
    core = make_core()
    image = tmp_path / "image.png"
    image.write_bytes(b"x")
    item = make_ctx()

    result = state.make_portable_image_path(core, str(image), ctx=item)

    assert result == f"local:{image}"
    core.filesystem.make_local.assert_called_once_with(str(image), ctx=item)


def test_remember_generated_image_path_uses_newest_valid_generated_image(monkeypatch):
    core = make_core()
    item = make_ctx(extra=None)
    monkeypatch.setattr(state, "make_portable_image_path", lambda core, value, ctx=None: {
        "old": "local:old",
        "new": "local:new",
    }.get(value))

    result = state.remember_generated_image_path(core, item, ["old", "invalid", "new"])

    assert result == "local:new"
    assert item.extra[state.LAST_GENERATED_IMAGE_PATH] == "local:new"


def test_remember_generated_image_path_handles_missing_context_or_paths():
    core = make_core()

    assert state.remember_generated_image_path(core, None, ["x"]) is None
    assert state.remember_generated_image_path(core, make_ctx(), []) is None


def test_remember_user_reference_image_path_persists_extra_and_visible_image_once(monkeypatch):
    core = make_core()
    item = make_ctx(extra=None, images=None)
    monkeypatch.setattr(state, "make_portable_image_path", lambda core, value, ctx=None: "local:ref")

    assert state.remember_user_reference_image_path(core, item, "ref") == "local:ref"
    assert state.remember_user_reference_image_path(core, item, "ref") == "local:ref"

    assert item.extra[state.LAST_USER_REFERENCE_IMAGE_PATH] == "local:ref"
    assert item.images == ["local:ref"]


def test_get_generated_path_from_ctx_prefers_explicit_cache_then_legacy_image_id(monkeypatch):
    core = make_core()
    monkeypatch.setattr(state, "make_portable_image_path", lambda core, value, ctx=None: {
        "cached": "portable:cached",
        "legacy": "portable:legacy",
    }.get(value))

    explicit = make_ctx(extra={state.LAST_GENERATED_IMAGE_PATH: "cached", "image_id": "legacy"})
    legacy = make_ctx(extra={"image_id": "legacy"})

    assert state._get_generated_path_from_ctx(core, explicit) == (True, "portable:cached")
    assert state._get_generated_path_from_ctx(core, legacy) == (True, "portable:legacy")
    assert state._get_generated_path_from_ctx(core, make_ctx(extra={})) == (False, None)


def test_get_generated_path_from_ctx_uses_images_when_remote_image_id_has_local_saved_copy(monkeypatch):
    core = make_core()
    monkeypatch.setattr(state, "make_portable_image_path", lambda core, value, ctx=None: "portable:local" if value == "local.png" else None)
    item = make_ctx(extra={"image_id": "https://remote/image"}, images=["bad.png", "local.png"])

    assert state._get_generated_path_from_ctx(core, item) == (True, "portable:local")


def test_get_last_generated_image_checks_live_context_first(monkeypatch):
    core = make_core()
    live = make_ctx(extra={state.LAST_GENERATED_IMAGE_PATH: "live"})
    old = make_ctx(extra={state.LAST_GENERATED_IMAGE_PATH: "old"})
    core.ctx.get_items.return_value = [old]
    monkeypatch.setattr(state, "_get_generated_path_from_ctx", lambda core, item: {
        id(live): (True, "portable:live"),
        id(old): (True, "portable:old"),
    }[id(item)])

    assert state.get_last_generated_image_path(core, live) == "portable:live"
    core.ctx.get_items.assert_not_called()


def test_get_last_generated_image_does_not_fall_back_past_newest_missing_generation(monkeypatch):
    core = make_core()
    older = object()
    newest = object()
    core.ctx.get_items.return_value = [older, newest]
    monkeypatch.setattr(state, "_get_generated_path_from_ctx", lambda core, item: {
        id(None): (False, None),
        id(newest): (True, None),
        id(older): (True, "portable:older"),
    }[id(item)])

    assert state.get_last_generated_image_path(core) is None


def test_get_user_reference_path_and_latest_reference_use_same_no_fallback_rule(monkeypatch):
    core = make_core()
    older = make_ctx(extra={state.LAST_USER_REFERENCE_IMAGE_PATH: "old"})
    newest = make_ctx(extra={state.LAST_USER_REFERENCE_IMAGE_PATH: "new"})
    core.ctx.get_items.return_value = [older, newest]
    monkeypatch.setattr(state, "make_portable_image_path", lambda core, value, ctx=None: "portable:old" if value == "old" else None)

    assert state._get_user_reference_path_from_ctx(core, older) == (True, "portable:old")
    assert state.get_last_user_reference_image_path(core) is None


def test_get_current_user_image_path_returns_newest_valid_active_attachment(monkeypatch):
    core = make_core()
    core.attachments.get_all.return_value = {
        "a": SimpleNamespace(path="old.png"),
        "b": SimpleNamespace(path="bad.txt"),
        "c": SimpleNamespace(path="new.png"),
    }
    monkeypatch.setattr(state, "make_portable_image_path", lambda core, value, ctx=None: {
        "old.png": "portable:old",
        "new.png": "portable:new",
    }.get(value))

    assert state.get_current_user_image_path(core, "chat") == "portable:new"
    core.attachments.get_all.assert_called_once_with("chat")


def test_get_current_user_image_path_handles_attachment_provider_failure():
    core = make_core()
    core.attachments.get_all.side_effect = RuntimeError("boom")

    assert state.get_current_user_image_path(core, "chat") is None
