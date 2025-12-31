#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #
import os
import pytest
from unittest.mock import MagicMock, patch
from pygpt_net.controller.chat.attachment import Attachment
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge import BridgeContext

class DummyUI:
    def __init__(self):
        self.nodes = {
            'input.attachments.ctx.mode.query': MagicMock(),
            'input.attachments.ctx.mode.query_summary': MagicMock(),
            'input.attachments.ctx.mode.full': MagicMock(),
            'input.attachments.ctx.mode.off': MagicMock()
        }
        self.chat = MagicMock()
        self.chat.input = MagicMock()
        self.chat.input.attachments_ctx = MagicMock()
        self.tabs = {'input': MagicMock()}
        self.dialogs = MagicMock()

class DummyCore:
    def __init__(self):
        self.config = MagicMock()
        self.config.get = MagicMock(return_value=False)
        self.config.set = MagicMock()
        self.config.save = MagicMock()
        self.attachments = MagicMock()
        self.attachments.has = MagicMock(return_value=False)
        self.attachments.get_all = MagicMock(return_value={})
        self.attachments.context = MagicMock()
        self.attachments.context.upload = MagicMock(return_value={'uuid': 'dummy', 'path': 'dummy.txt'})
        self.attachments.context.get_context = MagicMock(return_value="content")
        self.attachments.context.get_used_files = MagicMock(return_value=["file1"])
        self.attachments.context.get_used_urls = MagicMock(return_value=["url1"])
        self.attachments.context.reset = MagicMock()
        self.attachments.context.get_all = MagicMock(return_value=[])
        self.attachments.context.count = MagicMock(return_value=0)
        self.attachments.context.delete = MagicMock()
        self.attachments.context.clear = MagicMock()
        self.attachments.context.get_dir = MagicMock(return_value="dir")
        self.idx = MagicMock()
        self.idx.indexing = MagicMock(return_value=True)
        self.filesystem = MagicMock()
        self.filesystem.packer = MagicMock()
        self.filesystem.packer.is_archive = MagicMock(return_value=False)
        self.filesystem.packer.unpack = MagicMock(return_value=None)
        self.filesystem.packer.remove_tmp = MagicMock()
        self.filesystem.types = MagicMock()
        self.filesystem.types.is_image = MagicMock(return_value=False)
        self.ctx = MagicMock()
        self.ctx.get_current_meta = MagicMock(return_value=None)
        self.ctx.save = MagicMock()

class DummyController:
    def __init__(self):
        self.ctx = MagicMock()
        self.ui = MagicMock()
        self.ui.update_tokens = MagicMock()
        self.files = MagicMock()

class DummyWindow:
    def __init__(self):
        self.core = DummyCore()
        self.ui = DummyUI()
        self.controller = DummyController()
        self.threadpool = MagicMock()
        self.dispatch = MagicMock()

class DummyMeta:
    def __init__(self, additional_ctx=None, group=None):
        self.id = "meta1"
        self.additional_ctx = additional_ctx
        self.group = group
    def has_additional_ctx(self):
        return bool(self.additional_ctx)
    def get_additional_ctx(self):
        return self.additional_ctx if self.additional_ctx is not None else []

class DummyGroup:
    def __init__(self, additional_ctx=None):
        self.additional_ctx = additional_ctx

@pytest.fixture
def dummy_window():
    return DummyWindow()

@pytest.fixture
def dummy_meta():
    return DummyMeta(additional_ctx=[])

class TestAttachment:
    def test_has_true(self, dummy_window):
        file_obj = MagicMock()
        file_obj.path = "dummy.txt"
        dummy_window.core.attachments.has.return_value = True
        dummy_window.core.attachments.get_all.return_value = {"a": file_obj}
        dummy_window.core.idx.indexing.is_allowed.return_value = True
        dummy_window.core.filesystem.packer.is_archive.return_value = False
        dummy_window.core.filesystem.types.is_image.return_value = False
        att = Attachment(dummy_window)
        assert att.has("any") is True

    def test_has_false(self, dummy_window):
        file_obj = MagicMock()
        file_obj.path = "dummy.txt"
        dummy_window.core.attachments.has.return_value = True
        dummy_window.core.attachments.get_all.return_value = {"a": file_obj}
        att = Attachment(dummy_window)
        att.is_allowed = MagicMock(return_value=False)
        assert att.has("any") is False

    def test_setup(self, dummy_window):
        dummy_window.core.config.get = MagicMock(return_value=Attachment.MODE_FULL_CONTEXT)
        att = Attachment(dummy_window)
        att.setup()
        dummy_window.ui.nodes['input.attachments.ctx.mode.full'].setChecked.assert_called_with(True)
        dummy_window.core.config.get = MagicMock(return_value=Attachment.MODE_QUERY_CONTEXT)
        att.setup()
        dummy_window.ui.nodes['input.attachments.ctx.mode.query'].setChecked.assert_called_with(True)
        dummy_window.core.config.get = MagicMock(return_value=Attachment.MODE_QUERY_CONTEXT_SUMMARY)
        att.setup()
        dummy_window.ui.nodes['input.attachments.ctx.mode.query_summary'].setChecked.assert_called_with(True)
        dummy_window.core.config.get = MagicMock(return_value=Attachment.MODE_DISABLED)
        att.setup()
        dummy_window.ui.nodes['input.attachments.ctx.mode.off'].setChecked.assert_called_with(True)

    def test_reload(self, dummy_window):
        att = Attachment(dummy_window)
        att.setup = MagicMock()
        att.reload()
        att.setup.assert_called_once()

    def test_handle(self, dummy_window):
        att = Attachment(dummy_window)
        with patch('pygpt_net.controller.chat.attachment.AttachmentWorker') as MockWorker:
            worker = MagicMock()
            worker.signals = MagicMock()
            worker.signals.error = MagicMock()
            worker.signals.success = MagicMock()
            worker.signals.error.connect = MagicMock()
            worker.signals.success.connect = MagicMock()
            MockWorker.return_value = worker
            dummy_window.core.ctx.get_current_meta = MagicMock(return_value="meta")
            att.handle("m", "t")
            assert worker.mode == "m"
            assert worker.prompt == "t"
            worker.signals.error.connect.assert_called_with(att.handle_upload_error)
            worker.signals.success.connect.assert_called_with(att.handle_upload_success)
            dummy_window.threadpool.start.assert_called_with(worker)

    def test_is_allowed(self, dummy_window):
        dummy_window.core.config.get = MagicMock(return_value=False)
        dummy_window.core.idx.indexing.is_allowed.return_value = True
        dummy_window.core.filesystem.packer.is_archive.return_value = False
        dummy_window.core.filesystem.types.is_image.return_value = False
        att = Attachment(dummy_window)
        assert att.is_allowed("file") is True
        dummy_window.core.idx.indexing.is_allowed.return_value = False
        assert att.is_allowed("file") is False
        dummy_window.core.idx.indexing.is_allowed.return_value = True
        dummy_window.core.filesystem.types.is_image.return_value = True
        dummy_window.core.config.get = MagicMock(return_value=False)
        assert att.is_allowed("file") is False
        dummy_window.core.config.get = MagicMock(return_value=True)
        assert att.is_allowed("file") is True
        dummy_window.core.idx.indexing.is_allowed.return_value = False
        dummy_window.core.filesystem.packer.is_archive.return_value = True
        assert att.is_allowed("file") is True

    def test_upload(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        a = MagicMock()
        a.type = AttachmentItem.TYPE_FILE
        dummy_window.core.attachments.get_all.return_value = {"a": a}
        att.upload_file = MagicMock(return_value=True)
        dummy_window.core.config.get = MagicMock(return_value=False)
        res = att.upload(dummy_meta, "m", "p")
        assert res is True
        dummy_window.core.ctx.save.assert_called_with(dummy_meta.id)

    def test_upload_file_non_archive(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        a = MagicMock()
        a.path = "file.txt"
        att.is_allowed = MagicMock(return_value=True)
        dummy_window.core.filesystem.packer.is_archive.return_value = False
        dummy_window.core.attachments.context.upload.return_value = {"uuid": "id", "path": "file.txt"}
        att.append_to_meta = MagicMock()
        res = att.upload_file(a, dummy_meta, "p", False)
        assert res is True
        att.append_to_meta.assert_called()
        assert a.consumed is True

    def test_upload_file_archive(self, dummy_window, dummy_meta, monkeypatch):
        att = Attachment(dummy_window)
        a = MagicMock()
        a.path = "archive.zip"
        att.is_allowed = MagicMock(return_value=True)
        dummy_window.core.filesystem.packer.is_archive.return_value = True
        dummy_window.core.attachments.context.upload.return_value = {"uuid": "id", "path": "archive.zip"}
        att.append_to_meta = MagicMock()
        def fake_walk(p):
            return [("tmp_dir", [], ["file1.txt"])]
        monkeypatch.setattr(os, "walk", fake_walk)
        monkeypatch.setattr(os.path, "join", lambda *args: "/".join(args))
        monkeypatch.setattr(os.path, "basename", lambda p: p.split("/")[-1])
        monkeypatch.setattr(os.path, "relpath", lambda p, start: p[len(start)+1:] if p.startswith(start + "/") else p)
        monkeypatch.setattr(os.path, "getsize", lambda p: 100)
        att.is_verbose = MagicMock(return_value=True)
        res = att.upload_file(a, dummy_meta, "p", False)
        assert res is False
        # dummy_window.core.filesystem.packer.remove_tmp.assert_called_with("tmp_dir")

    def test_append_to_meta(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        item = {"k": "v"}
        dummy_meta.additional_ctx = None
        att.append_to_meta(dummy_meta, item)
        assert dummy_meta.additional_ctx is not None
        dummy_meta.additional_ctx = []
        group = DummyGroup()
        dummy_meta.group = group
        att.append_to_meta(dummy_meta, item)
        assert group.additional_ctx is not None

    def test_upload_web(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        a = MagicMock()
        a.path = "file.txt"
        att.upload_file = MagicMock(return_value=True)
        res = att.upload_web(a, dummy_meta, "p", False)
        assert res is True

    def test_has_context(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        dummy_meta.has_additional_ctx = MagicMock(return_value=True)
        assert att.has_context(dummy_meta) is True
        assert att.has_context(None) is False

    def test_current_has_context(self, dummy_window, dummy_meta):
        dummy_window.core.ctx.get_current_meta = MagicMock(return_value=dummy_meta)
        att = Attachment(dummy_window)
        att.has_context = MagicMock(return_value=True)
        assert att.current_has_context() is True

    def test_get_mode(self, dummy_window):
        att = Attachment(dummy_window)
        att.mode = "custom"
        assert att.get_mode() == "custom"

    def test_get_context(self, dummy_window):
        att = Attachment(dummy_window)
        att.is_verbose = MagicMock(return_value=True)
        ctx = MagicMock()
        history = []
        dummy_window.core.attachments.context.get_context.return_value = "data"
        dummy_window.core.attachments.context.get_used_files.return_value = ["f1"]
        dummy_window.core.attachments.context.get_used_urls.return_value = ["u1"]
        res = att.get_context(ctx, history)
        assert "ADDITIONAL CONTEXT FROM ATTACHMENT(s): data" in res

    def test_update(self, dummy_window, dummy_meta):
        dummy_window.core.config.get = MagicMock(return_value="assistant")
        att = Attachment(dummy_window)
        att.hide_uploaded = MagicMock()
        att.update()
        att.hide_uploaded.assert_called_once()
        dummy_window.core.config.get = MagicMock(return_value="other")
        dummy_window.core.ctx.get_current_meta = MagicMock(return_value=dummy_meta)
        att.update_list = MagicMock()
        att.update()
        att.update_list.assert_called_with(dummy_meta)

    def test_update_list(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        att.update_tab = MagicMock()
        att.update_list(dummy_meta)
        dummy_window.ui.chat.input.attachments_ctx.update.assert_called()

    def test_update_tab(self, dummy_window, dummy_meta):
        dummy_meta.has_additional_ctx = MagicMock(return_value=True)
        dummy_window.core.attachments.context.get_all.return_value = []
        dummy_window.core.attachments.context.count.return_value = 2
        att = Attachment(dummy_window)
        att.update_tab(dummy_meta)
        dummy_window.ui.tabs['input'].setTabText.assert_called()

    def test_is_verbose(self, dummy_window):
        dummy_window.core.config.get = MagicMock(return_value=True)
        att = Attachment(dummy_window)
        assert att.is_verbose() is True

    def test_show_uploaded(self, dummy_window):
        att = Attachment(dummy_window)
        att.uploaded_tab_idx = 3
        att.show_uploaded()
        # dummy_window.ui.tabs['input'].setTabVisible.assert_called_with(3, True)

    def test_hide_uploaded(self, dummy_window):
        att = Attachment(dummy_window)
        att.uploaded_tab_idx = 3
        att.hide_uploaded()
        # dummy_window.ui.tabs['input'].setTabVisible.assert_called_with(3, False)

    def test_delete_by_idx(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        att.window.core.ctx.get_current_meta = MagicMock(return_value=dummy_meta)
        dummy_meta.has_additional_ctx = MagicMock(return_value=False)
        att.delete_by_idx(0, force=False)
        dummy_window.ui.dialogs.confirm.assert_called()
        dummy_meta.additional_ctx = [{"k": "v"}]
        dummy_window.core.attachments.context.get_all.return_value = [{"k": "v"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        att.delete_by_idx(0, force=True)
        # dummy_window.core.attachments.context.delete.assert_called()
        # dummy_window.controller.ctx.update.assert_called()

    def test_clear(self, dummy_window, dummy_meta):
        att = Attachment(dummy_window)
        att.clear(force=False)
        dummy_window.ui.dialogs.confirm.assert_called()
        dummy_meta.additional_ctx = [{"k": "v"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        att.clear(force=True, remove_local=True)
        dummy_window.core.attachments.context.clear.assert_called_with(dummy_meta, delete_files=True)
        dummy_window.controller.ctx.update.assert_called()

    def test_select(self, dummy_window):
        att = Attachment(dummy_window)
        att.select(0)

    def test_open_by_idx(self, dummy_window, dummy_meta, monkeypatch):
        dummy_meta.additional_ctx = [{"path": "file.txt"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        dummy_window.core.attachments.context.get_all.return_value = dummy_meta.additional_ctx
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "isfile", lambda p: True)
        att = Attachment(dummy_window)
        att.open_by_idx(0)
        dummy_window.controller.files.open.assert_called_with("file.txt")

    def test_open_dir_src_by_idx(self, dummy_window, dummy_meta, monkeypatch):
        dummy_meta.additional_ctx = [{"path": "dir/file.txt"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        dummy_window.core.attachments.context.get_all.return_value = dummy_meta.additional_ctx
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "isdir", lambda p: True)
        monkeypatch.setattr(os.path, "dirname", lambda p: "dir")
        att = Attachment(dummy_window)
        att.open_dir_src_by_idx(0)
        dummy_window.controller.files.open.assert_called_with("dir")

    def test_open_dir_dest_by_idx(self, dummy_window, dummy_meta, monkeypatch):
        dummy_meta.additional_ctx = [{"uuid": "uid", "path": "file.txt"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        dummy_window.core.attachments.context.get_all.return_value = dummy_meta.additional_ctx
        dummy_window.core.attachments.context.get_dir.return_value = "root_dir"
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "isdir", lambda p: True)
        monkeypatch.setattr(os.path, "join", lambda *args: "/".join(args))
        att = Attachment(dummy_window)
        att.open_dir_dest_by_idx(0)
        dummy_window.controller.files.open.assert_called_with("root_dir/uid")

    def test_has_file_by_idx(self, dummy_window, dummy_meta, monkeypatch):
        dummy_meta.additional_ctx = [{"path": "file.txt"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        dummy_window.core.attachments.context.get_all.return_value = dummy_meta.additional_ctx
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "isfile", lambda p: True)
        att = Attachment(dummy_window)
        assert att.has_file_by_idx(0) is True
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        assert att.has_file_by_idx(0) is False

    def test_has_src_by_idx(self, dummy_window, dummy_meta, monkeypatch):
        dummy_meta.additional_ctx = [{"real_path": "dir/file.txt", "path": "dir/file.txt"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        dummy_window.core.attachments.context.get_all.return_value = dummy_meta.additional_ctx
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "isdir", lambda p: True)
        att = Attachment(dummy_window)
        assert att.has_src_by_idx(0) is True

    def test_has_dest_by_idx(self, dummy_window, dummy_meta, monkeypatch):
        dummy_meta.additional_ctx = [{"uuid": "uid", "path": "file.txt"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        dummy_window.core.attachments.context.get_all.return_value = dummy_meta.additional_ctx
        dummy_window.core.attachments.context.get_dir.return_value = "root_dir"
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        monkeypatch.setattr(os.path, "isdir", lambda p: True)
        monkeypatch.setattr(os.path, "join", lambda *args: "/".join(args))
        att = Attachment(dummy_window)
        assert att.has_dest_by_idx(0) is True

    def test_get_current_tokens(self, dummy_window, dummy_meta):
        dummy_meta.additional_ctx = [{"tokens": "5"}, {"tokens": "notanumber"}]
        dummy_window.core.ctx.get_current_meta.return_value = dummy_meta
        att = Attachment(dummy_window)
        att.mode = Attachment.MODE_FULL_CONTEXT
        tokens = att.get_current_tokens()
        assert tokens == 5

    def test_handle_upload_error(self, dummy_window):
        att = Attachment(dummy_window)
        err = Exception("error")
        att.window.dispatch = MagicMock()
        att.handle_upload_error(err)
        event = att.window.dispatch.call_args[0][0]
        assert event.data["msg"] == "Error reading attachments: error"

    def test_handle_upload_success(self, dummy_window):
        att = Attachment(dummy_window)
        att.window.dispatch = MagicMock()
        att.handle_upload_success("txt")
        event = att.window.dispatch.call_args[0][0]
        ctx = event.data["context"]
        assert isinstance(ctx, BridgeContext)
        assert ctx.prompt == "txt"

    def test_switch_mode(self, dummy_window):
        att = Attachment(dummy_window)
        att.window.core.config.set = MagicMock()
        att.window.core.config.save = MagicMock()
        att.window.controller.ui.update_tokens = MagicMock()
        att.switch_mode("new")
        assert att.mode == "new"
        att.window.core.config.set.assert_called_with("ctx.attachment.mode", "new")
        att.window.core.config.save.assert_called_once()
        att.window.controller.ui.update_tokens.assert_called_once()