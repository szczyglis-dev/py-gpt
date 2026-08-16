#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.16 19:55:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.attachments.native import Native
from pygpt_net.core.types import MODE_CHAT
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.model import ModelItem


def make_window(config=None, model=None):
    config = dict(config or {})
    window = SimpleNamespace()
    window.core = SimpleNamespace()
    window.core.config = SimpleNamespace()
    window.core.config.get = lambda key, default=None: config.get(key, default)
    window.core.models = SimpleNamespace()
    window.core.models.get = MagicMock(return_value=model)
    window.core.api = SimpleNamespace()
    window.core.api.openai = SimpleNamespace(get_client=MagicMock())
    window.core.api.google = SimpleNamespace(get_client=MagicMock())
    window.core.api.anthropic = SimpleNamespace(get_client=MagicMock())
    window.core.api.xai = SimpleNamespace(get_client=MagicMock())
    window.core.ctx = SimpleNamespace(get_current_meta=MagicMock(return_value=None))
    return window


def make_model(provider="openai", model_id="gpt-test", image=False):
    model = ModelItem()
    model.id = model_id
    model.provider = provider
    model.input = ["text", "image"] if image else ["text"]
    model.mode = ["chat"]
    return model


def test_get_provider_requires_preference():
    model = make_model("openai")
    native = Native(make_window({"ctx.attachment.native_upload": False}, model))
    assert native.get_provider(MODE_CHAT, model) is None


def test_get_provider_native_sdks():
    google = make_model("google", "gemini-test")
    native = Native(make_window({
        "ctx.attachment.native_upload": True,
        "api_native_google": True,
        "api_native_google.use_vertex": False,
    }, google))
    assert native.get_provider(MODE_CHAT, google) == "google"

    anthropic = make_model("anthropic", "claude-test")
    native = Native(make_window({
        "ctx.attachment.native_upload": True,
        "api_native_anthropic": True,
    }, anthropic))
    assert native.get_provider(MODE_CHAT, anthropic) == "anthropic"

    xai = make_model("x_ai", "grok-4.5")
    native = Native(make_window({
        "ctx.attachment.native_upload": True,
        "api_native_xai": True,
    }, xai))
    assert native.get_provider(MODE_CHAT, xai) == "x_ai"


def test_google_vertex_disables_file_api_route():
    model = make_model("google", "gemini-test")
    native = Native(make_window({
        "ctx.attachment.native_upload": True,
        "api_native_google": True,
        "api_native_google.use_vertex": True,
    }, model))
    assert native.get_provider(MODE_CHAT, model) is None


def test_can_upload_openai_text_and_pdf_requires_image_input(tmp_path):
    txt = tmp_path / "test.txt"
    txt.write_text("hello", encoding="utf-8")
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-test")

    model = make_model("openai", image=False)
    native = Native(make_window({"ctx.attachment.native_upload": True}, model))
    assert native.can_upload(str(txt), MODE_CHAT, model) is True
    assert native.can_upload(str(pdf), MODE_CHAT, model) is False

    model.input.append("image")
    assert native.can_upload(str(pdf), MODE_CHAT, model) is True


def test_upload_openai_uses_user_data_purpose(tmp_path):
    path = tmp_path / "test.txt"
    path.write_text("hello", encoding="utf-8")
    model = make_model("openai")
    window = make_window({"ctx.attachment.native_upload": True}, model)
    client = SimpleNamespace()
    client.files = SimpleNamespace()
    client.files.create = MagicMock(return_value=SimpleNamespace(id="file_123"))
    window.core.api.openai.get_client.return_value = client
    native = Native(window)

    ref = native.upload(str(path), MODE_CHAT, model)

    assert ref["provider"] == "openai"
    assert ref["id"] == "file_123"
    assert ref["name"] == "test.txt"
    _, kwargs = client.files.create.call_args
    assert kwargs["purpose"] == "user_data"


def test_google_mime_maps_code_to_text_plain():
    assert Native._google_mime("script.py") == "text/plain"
    assert Native._google_mime("README.md") == "text/plain"
    assert Native._google_mime("data.json") == "application/json"


def test_get_refs_deduplicates_current_and_persisted_refs():
    model = make_model("openai")
    window = make_window({
        "ctx.attachment.native_upload": True,
        "ctx.attachment.append_once": False,
    }, model)
    attachment = AttachmentItem()
    attachment.extra = {
        "native_files": [
            {"provider": "openai", "id": "file_123", "name": "test.txt"}
        ]
    }
    meta = SimpleNamespace()
    meta.get_additional_ctx = MagicMock(return_value=[{
        "type": "native_file",
        "native_provider": "openai",
        "native_id": "file_123",
        "native_uri": None,
        "native_mime_type": "text/plain",
        "name": "test.txt",
        "size": 5,
    }])
    window.core.ctx.get_current_meta.return_value = meta
    native = Native(window)

    refs = native.get_refs({"a": attachment}, "openai")

    assert len(refs) == 1
    assert refs[0]["id"] == "file_123"


def test_get_refs_include_meta_false_skips_persisted_refs():
    model = make_model("openai")
    window = make_window({"ctx.attachment.native_upload": True}, model)
    meta = SimpleNamespace()
    meta.get_additional_ctx = MagicMock(return_value=[{
        "type": "native_file",
        "native_provider": "openai",
        "native_id": "file_meta",
    }])
    window.core.ctx.get_current_meta.return_value = meta
    native = Native(window)

    assert native.get_refs({}, "openai", include_meta=False) == []
    window.core.ctx.get_current_meta.assert_not_called()
