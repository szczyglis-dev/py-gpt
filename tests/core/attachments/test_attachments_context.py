#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch, mock_open

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.model import ModelItem
from tests.mocks import mock_window
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.core.attachments.context import Context


def mock_get(key, default=None):
    if key == "ctx.attachment.rag.history":
        return True
    elif key == "ctx.attachment.rag.history.max_items":
        return 3
    elif key == "ctx.attachment.summary.model":
        return "model_summary"
    elif key == "ctx.attachment.query.model":
        return "model_query"
    elif key == "ctx.attachment.verbose":
        return True

def test_get_context(mock_window):
    """Test get context"""
    history = []
    ctx = CtxItem()
    mock_window.controller.chat.attachment.MODE_FULL_CONTEXT = "full"
    mock_window.controller.chat.attachment.MODE_QUERY_CONTEXT = "query"
    mock_window.controller.chat.attachment.MODE_QUERY_CONTEXT_SUMMARY = "summary"
    context = Context(mock_window)
    context.get_context_text = MagicMock(return_value="test1")
    context.query_context = MagicMock(return_value="test2")
    context.summary_context = MagicMock(return_value="test3")

    mode = "full"
    result = context.get_context(mode, ctx, history)
    assert result == "test1"

    mode = "query"
    result = context.get_context(mode, ctx, history)
    assert result == "test2"

    mode = "summary"
    result = context.get_context(mode, ctx, history)
    assert result == "test3"


def test_get_context_text(mock_window):
    """Test get context text"""
    ctx = CtxItem()
    meta = CtxMeta()
    meta.additional_ctx = [
        {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
        }
    ]
    ctx.meta = meta
    with patch("os.path.exists", return_value=True), \
            patch('os.path.isdir', return_value=True):
        with patch('builtins.open', mock_open(read_data='test_text')) as mock_file:
            mock_file.read = MagicMock(return_value="test_text")
            context = Context(mock_window)
            result = context.get_context_text(ctx, filename=True)
            assert result == "Filename: test_name\n\ntest_text\n\n"
            assert context.last_files == ["test_real_path"]
            assert context.last_used_content == result
            assert context.last_used_context == result

def test_query_context(mock_window):
    """Test query context"""
    history = []
    ctx = CtxItem()
    meta = CtxMeta()
    meta.additional_ctx = [
        {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
            "indexed": False,
        }
    ]
    ctx.meta = meta
    with patch("os.path.exists", return_value=True), \
            patch('os.path.isdir', return_value=True):
        with patch('builtins.open', mock_open(read_data='test_text')) as mock_file:
            mock_file.read = MagicMock(return_value="test_text")
            mock_window.core.idx.chat.query_attachment = MagicMock(return_value="test_text")
            context = Context(mock_window)
            context.index_attachment = MagicMock(return_value=["doc_uuid"])
            result = context.query_context(ctx, history)
            assert result == "test_text"
            assert context.index_attachment.called_once()
            assert mock_window.core.ctx.replace.called_once()
            assert mock_window.core.ctx.save.called_once()

def test_summary_context(mock_window):
    """Test summary context"""
    history = []
    ctx = CtxItem()
    meta = CtxMeta()
    model_item = ModelItem()
    meta.additional_ctx = [
        {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
            "indexed": False,
        }
    ]
    ctx.meta = meta
    context = Context(mock_window)
    context.get_selected_model = MagicMock(return_value=model_item)
    context.get_context_text = MagicMock(return_value="test_text")
    context.prepare_context_history = MagicMock(return_value=[])
    result = context.query_context(ctx, history)
    assert mock_window.dispatch.called_once()


def test_prepare_context_history(mock_window):
    """Test prepare_context_history"""
    item1 = CtxItem()
    item2 = CtxItem()
    item3 = CtxItem()
    item4 = CtxItem()
    history = [
        item1,
        item2,
        item3,
        item4,
    ]
    mock_window.core.config.get = MagicMock()
    mock_window.core.config.get.side_effect = mock_get  # max 3 items
    context = Context(mock_window)
    result = context.prepare_context_history(history)
    assert len(result) == 3


def test_upload(mock_window):
    """Test upload"""
    ctx = CtxItem()
    meta = CtxMeta()
    ctx.meta = meta
    attachment = AttachmentItem()
    attachment.uuid = "test_uuid"
    attachment.name = "test_name"
    attachment.path = "test_path"
    with patch("os.makedirs", return_value=True), \
            patch('os.path.getsize', return_value=123):
        with patch('builtins.open', mock_open()) as mock_file:
            mock_window.core.tokens.from_str = MagicMock(return_value=4321)
            mock_file.write = MagicMock()
            context = Context(mock_window)
            context.store_content = MagicMock(return_value=("test_src", []))
            context.read_content = MagicMock(return_value=("test_content", []))
            context.index_attachment = MagicMock(return_value=["doc_uuid"])
            result = context.upload(
                meta,
                attachment,
                "prompt",
                auto_index=False,
                real_path = "test_real_path"
            )
            assert result["name"] == "test_path"  # basename(path)
            assert result["type"] == "local_file"
            assert result["path"] == "test_path"
            assert result["real_path"] == "test_real_path"
            assert result["indexed"] == False


def test_read_content(mock_window):
    """Test read_content"""
    attachment = AttachmentItem()
    attachment.path = "test_path"
    attachment.type = "file"
    mock_window.core.idx.indexing.read_text_content = MagicMock(return_value=("test_content", []))
    context = Context(mock_window)
    result, _ = context.read_content(attachment, "test_path", "test_prompt")
    assert result == "test_content"


def test_store_content(mock_window):
    """Test store_content"""
    attachment = AttachmentItem()
    attachment.path = "test_path"
    attachment.type = "url"
    mock_window.core.idx.indexing.read_web_content = MagicMock(return_value=("test_content", []))
    with patch("os.path.exists", return_value=True), \
            patch('os.remove', return_value=True):
        with patch('builtins.open', mock_open()) as mock_file:
            context = Context(mock_window)
            result, _ = context.store_content(attachment, "test_dir")
            assert result == "test_dir/url.txt"


def test_index_attachment(mock_window):
    """Test index attachment"""
    mock_window.core.idx.indexing.index_attachment = MagicMock(return_value=["doc_uuid"])
    context = Context(mock_window)
    result = context.index_attachment("file", "test_src", "test_idx_path")
    assert result == ["doc_uuid"]


def test_get_all(mock_window):
    """Test get_all"""
    meta = CtxMeta()
    meta.additional_ctx = [
        {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
        }
    ]
    context = Context(mock_window)
    result = context.get_all(meta)
    assert result == meta.additional_ctx


def test_get_selected_model(mock_window):
    """Test get selected model"""
    mock_window.core.config.get = MagicMock()
    mock_window.core.config.get.side_effect = mock_get
    context = Context(mock_window)
    result, _ = context.get_selected_model("query")
    assert result == "model_query"


def test_duplicate(mock_window):
    """Test get selected model"""
    mock_window.core.ctx.get_meta_by_id = MagicMock(return_value=CtxMeta())
    mock_window.core.ctx.save = MagicMock()
    with patch("os.path.exists", return_value=True), \
            patch("os.path.isdir", return_value=True), \
            patch('shutil.copytree', return_value=True):
                context = Context(mock_window)
                result = context.duplicate(11, 22)
                assert result == True


def test_count(mock_window):
    """Test count"""
    meta = CtxMeta()
    meta.additional_ctx = [
        {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
        }
    ]
    context = Context(mock_window)
    result = context.count(meta)
    assert result == 1


def test_delete(mock_window):
    """Test delete"""
    meta = CtxMeta()
    item = {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
        }
    meta.additional_ctx = [
        item
    ]
    mock_window.core.ctx.save = MagicMock()
    context = Context(mock_window)
    context.delete_local = MagicMock(return_value=True)
    context.delete_index = MagicMock(return_value=True)

    result = context.delete(meta, item, True)
    context.delete_local.assert_called_once()
    context.delete_index.assert_called_once()


def delete_by_meta(mock_window):
    """Test delete by meta"""
    meta = CtxMeta()
    context = Context(mock_window)
    context.delete_local = MagicMock(return_value=True)
    context.delete_by_meta(meta)
    context.delete_local.assert_called_once()


def delete_by_meta_id(mock_window):
    """Test delete by meta_id"""
    meta = CtxMeta()
    mock_window.core.ctx.get_meta_by_id = MagicMock(return_value=meta)
    context = Context(mock_window)
    context.delete_index = MagicMock(return_value=True)
    context.delete_by_meta(meta)
    context.delete_index.assert_called_once()


def reset_by_meta(mock_window):
    """Test reset by meta"""
    meta = CtxMeta()
    context = Context(mock_window)
    mock_window.core.ctx.save = MagicMock()
    context.delete_index = MagicMock(return_value=True)
    context.reset_by_meta(meta)
    context.delete_index.assert_called_once()
    mock_window.core.ctx.save.assert_called_once()


def reset_by_meta_id(mock_window):
    """Test reset by meta_id"""
    meta = CtxMeta()
    mock_window.core.ctx.get_meta_by_id = MagicMock(return_value=meta)
    context = Context(mock_window)
    context.delete_index = MagicMock(return_value=True)
    context.reset_by_meta_id(123)
    context.delete_index.assert_called_once()


def clear(mock_window):
    """Test clear"""
    meta = CtxMeta()
    meta.additional_ctx = [
        {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
        }
    ]
    context = Context(mock_window)
    mock_window.core.ctx.save = MagicMock()
    context.delete_index = MagicMock(return_value=True)
    context.clear(meta)
    context.delete_index.assert_called_once()
    mock_window.core.ctx.save.assert_called_once()
    assert len(meta.additional_ctx) == 0


def test_delete_index(mock_window):
    """Test delete_index"""
    meta = CtxMeta()
    with patch("os.path.exists", return_value=True), \
            patch("os.path.isdir", return_value=True), \
            patch('shutil.rmtree', return_value=True) as shutil_rmtree:
                context = Context(mock_window)
                result = context.delete_index(meta)
                shutil_rmtree.assert_called_once()


def test_delete_local(mock_window):
    """Test delete_local"""
    meta = CtxMeta()
    item = {
            "uuid": "test_uuid",
            "name": "test_name",
            "type": "local_file",
            "path": "test_path",
            "real_path": "test_real_path",
        }
    with patch("os.path.exists", return_value=True), \
            patch("os.path.isdir", return_value=True), \
            patch("os.remove", return_value=True) as os_remove, \
            patch("os.rmdir", return_value=True) as os_rmdir, \
            patch("os.listdir", return_value=["test_file"]) as os_listdir:
                context = Context(mock_window)
                context.delete_local(meta, item)
                os_remove.assert_called_once()
                os_rmdir.assert_called_once()


def test_truncate(mock_window):
    """Test truncate"""
    with patch("os.path.exists", return_value=True), \
            patch("os.path.isdir", return_value=True), \
            patch("os.makedirs", return_value=True) as os_makedirs, \
            patch("shutil.rmtree", return_value=True) as shutil_rmtree:
                context = Context(mock_window)
                context.truncate()
                shutil_rmtree.assert_called_once()
                os_makedirs.assert_called()


def test_reset(mock_window):
    """Test reset"""
    context = Context(mock_window)
    context.reset()
    assert context.last_used_item is None
    assert context.last_used_content is None
    assert context.last_used_context is None
    assert context.last_files == []
    assert context.last_urls == []


def test_get_used_files(mock_window):
    """Test reset"""
    context = Context(mock_window)
    context.last_files = ["test_file"]
    result = context.get_used_files()
    assert result == ["test_file"]


def test_get_used_urls(mock_window):
    """Test reset"""
    context = Context(mock_window)
    context.last_urls = ["test_url"]
    result = context.get_used_urls()
    assert result == ["test_url"]


def test_is_verbose(mock_window):
    """Test is verbose"""
    mock_window.core.config.get = MagicMock()
    mock_window.core.config.get.side_effect = mock_get
    context = Context(mock_window)
    result = context.is_verbose()
    assert result == True


def test_get_dir(mock_window):
    """Test get dir"""
    meta = CtxMeta()
    meta.uuid = "test_uuid"
    expected = os.path.join(mock_window.core.config.get_user_dir("ctx_idx"), "test_uuid")
    context = Context(mock_window)
    result = context.get_dir(meta)
    assert result == expected
