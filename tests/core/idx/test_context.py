#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.core.idx.context import Context


def test_get_messages(mock_window):
    """Test get messages"""
    item1 = CtxItem()
    item1.input = "test1"
    item1.output = "test2"
    item2 = CtxItem()
    item2.input = "test3"
    item2.output = "test4"
    items = [item1, item2]
    mock_window.core.ctx.get_history = MagicMock(return_value=items)
    mock_window.core.config.set('max_total_tokens', 100)
    mock_window.core.config.set('use_context', True)
    mock_window.core.models.get_num_ctx = MagicMock(return_value=100)
    mock_window.core.tokens.from_user = MagicMock(return_value=10)
    ctx = Context(mock_window)
    input_prompt = "test"
    system_prompt = "test"

    messages = ctx.get_messages(input_prompt, system_prompt)
    assert len(messages) == 4
    assert messages[0].role == "user"
    assert messages[0].content == "test1"
    assert messages[1].role == "assistant"
    assert messages[1].content == "test2"
    assert messages[2].role == "user"
    assert messages[2].content == "test3"
    assert messages[3].role == "assistant"
    assert messages[3].content == "test4"


def test_add_runtime_images_promotes_only_transport_images(tmp_path, monkeypatch, mock_window):
    from pygpt_net.item.attachment import AttachmentItem
    import pygpt_net.core.idx.context as context_module

    image = tmp_path / "runtime.png"
    image.write_bytes(b"png")
    normal = tmp_path / "normal.png"
    normal.write_bytes(b"png")
    text = tmp_path / "runtime.txt"
    text.write_text("x")
    monkeypatch.setattr(context_module, "is_image", lambda path: str(path).endswith(".png"))

    runtime = AttachmentItem(
        id="runtime", path=str(image), extra={"runtime_tool_attachment": True},
    )
    ordinary = AttachmentItem(
        id="ordinary", path=str(normal), extra={},
    )
    non_image = AttachmentItem(
        id="text", path=str(text), extra={"runtime_tool_attachment": True},
    )

    core = Context(mock_window)
    message = core.add_runtime_images({"r": runtime, "o": ordinary, "t": non_image})

    assert message is not None
    assert message.role == "user"
    assert "Inspect and use their visual content now" in message.blocks[0].text
    assert [str(block.path) for block in message.blocks[1:]] == [str(image)]
    assert core.get_attachments() == {}


def test_add_runtime_images_returns_none_for_missing_or_non_runtime_files(tmp_path, mock_window):
    from pygpt_net.item.attachment import AttachmentItem

    ordinary = tmp_path / "ordinary.png"
    ordinary.write_bytes(b"png")
    core = Context(mock_window)

    assert core.add_runtime_images({
        "ordinary": AttachmentItem(path=str(ordinary), extra={}),
        "missing": AttachmentItem(path=str(tmp_path / "missing.png"), extra={"runtime_tool_attachment": True}),
    }) is None


def test_extract_urls_and_accessors_keep_only_image_urls_for_mixed_text(mock_window):
    core = Context(mock_window)
    text = "see https://example.com/a.png and https://example.com/page"
    assert core.extract_urls(text) == ["https://example.com/a.png"]
    assert core.extract_urls("https://example.com/page") == ["https://example.com/page"]

    core.attachments = {"a": "/tmp/a.png"}
    core.urls = ["https://example.com/a.png"]
    assert core.get_attachments() == {"a": "/tmp/a.png"}
    assert core.get_urls() == ["https://example.com/a.png"]
