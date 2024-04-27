#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.27 10:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from tests.mocks import mock_window
from pygpt_net.controller.assistant.files import Files


def test_update(mock_window):
    """Test update files list"""
    files = Files(mock_window)
    files.update_list = MagicMock()
    files.update()
    files.update_list.assert_called_once()


def test_select(mock_window):
    """Test select file"""
    files = Files(mock_window)
    item = AssistantItem()
    mock_window.core.config.data = {"assistant": "assistant_id"}
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.files.get_file_id_by_idx = MagicMock(return_value="file_id")
    files.select(0)
    mock_window.core.assistants.get_by_id.assert_called_once()
    assert mock_window.core.assistants.current_file == "file_id"


def test_count_upload(mock_window):
    """Test upload file"""
    files = Files(mock_window)
    item = AttachmentItem()
    item.send = False
    item2 = AttachmentItem()
    item2.send = True
    attachments = {"id": item, "id2": item2}

    result = files.count_upload(attachments)
    assert result == 1


def test_import_files(mock_window):
    """Test import files"""
    mock_window.core.gpt.assistants.importer.import_files = MagicMock()
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    files.import_files(item)
    mock_window.core.gpt.assistants.importer.import_files.assert_called_once_with(item)


def test_download(mock_window):
    """Test download file"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    mock_window.core.config.data['assistant'] = "assistant_id"

    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.files.get_file_id_by_idx = MagicMock(return_value="file_id")
    mock_window.controller.attachment.download = MagicMock()

    files.download(0)
    mock_window.core.assistants.get_by_id.assert_called_once()
    mock_window.controller.attachment.download.assert_called_once_with("file_id")


def test_rename(mock_window):
    """Test rename file"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    mock_window.core.config.data['assistant'] = "assistant_id"
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.files.get_file_id_by_idx = MagicMock(return_value="file_id")
    mock_window.core.assistants.get_file_by_id = MagicMock(return_value={"name": "file_name"})

    mock_window.ui.dialog['rename'].id = None
    mock_window.ui.dialog['rename'].input.setText = MagicMock()
    mock_window.ui.dialog['rename'].show = MagicMock()
    mock_window.ui.dialog['rename'].accept = MagicMock()
    files.update = MagicMock()
    files.rename(0)

    mock_window.core.assistants.get_by_id.assert_called_once()
    mock_window.ui.dialog['rename'].input.setText.assert_called_once()
    assert mock_window.ui.dialog['rename'].id == "attachment_uploaded"
    files.update.assert_called_once()


def test_rename_close(mock_window):
    """Test close rename dialog"""
    files = Files(mock_window)
    files.update = MagicMock()
    files.rename_close()
    files.update.assert_called_once()


def test_update_name(mock_window):
    """Test update file name"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    mock_window.core.config.data['assistant'] = "assistant_id"
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.files.get_file_id_by_idx = MagicMock(return_value="file_id")
    mock_window.core.assistants.get_file_by_id = MagicMock(return_value={"name": "file_name"})
    mock_window.core.assistants.rename_file = MagicMock()

    mock_window.ui.dialog['rename'].id = "attachment_uploaded"
    mock_window.ui.dialog['rename'].input.text = "new_name"
    files.rename_close = MagicMock()
    files.update_name("file_id", "new_name")
    files.rename_close.assert_called_once()


def test_clear(mock_window):
    """Test clear files"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    item.files = {
        "file_id1": {},
    }
    mock_window.core.config.data['assistant'] = "assistant_id"
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.files.get_file_id_by_idx = MagicMock(return_value="file_id1")
    mock_window.core.assistants.get_file_by_id = MagicMock(return_value={"name": "file_name"})
    mock_window.core.assistants.has = MagicMock(return_value=True)
    mock_window.core.assistants.save = MagicMock()
    files.update = MagicMock()

    files.clear(force=True)
    mock_window.core.assistants.get_by_id.assert_called_once()
    files.update.assert_called_once()


def test_delete(mock_window):
    """Test delete file"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    item.files = {
        "file_id1": {},
    }
    mock_window.core.config.data['assistant'] = "assistant_id"
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.assistants.files.get_file_id_by_idx = MagicMock(return_value="file_id1")
    mock_window.core.assistants.get_file_by_id = MagicMock(return_value={"name": "file_name"})
    mock_window.core.assistants.save = MagicMock()
    mock_window.core.assistants.has = MagicMock(return_value=True)
    files.update = MagicMock()

    files.delete(0, force=True)
    mock_window.core.assistants.get_by_id.assert_called_once()
    files.update.assert_called_once()


def test_clear_attachments(mock_window):
    """Test clear attachments"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    item.attachments = {
        "attachment_id1": {},
    }
    mock_window.core.assistants.save = MagicMock()
    files.update = MagicMock()
    files.clear_attachments(item)
    mock_window.core.assistants.save.assert_called_once()
    files.update.assert_called_once()


def test_upload(mock_window):
    """Test upload attachments"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"

    os.path.exists = MagicMock(return_value=True)
    os.path.getsize = MagicMock(return_value=100)

    att = AttachmentItem()
    att.id = "attachment_id1"
    att.name = "attachment_id1"
    att.path = "attachment_id1"
    att.size = 100
    att.send = False

    attachments = {}
    attachments["attachment_id1"] = att

    mock_window.core.config.data['assistant'] = "assistant_id"
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    mock_window.core.gpt.assistants.file_upload = MagicMock(return_value="new_id")
    files.update_list = MagicMock()
    mock_window.core.assistants.save = MagicMock()
    mock_window.controller.attachment.update = MagicMock()

    num = files.upload("assistant", attachments)
    assert num == 1


def test_append(mock_window):
    """Test append attachment"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"

    att = AttachmentItem()
    att.id = "attachment_id1"
    att.name = "attachment_id1"

    mock_window.core.assistants.save = MagicMock()
    files.append(item, att)
    assert item.attachments["attachment_id1"].id == "attachment_id1"


def test_update_list(mock_window):
    """Test update list"""
    files = Files(mock_window)
    item = AssistantItem()
    item.id = "assistant_id"
    item.files = {
        "file_id1": {},
    }
    mock_window.core.config.data['assistant'] = "assistant_id"
    mock_window.core.assistants.get_by_id = MagicMock(return_value=item)
    files.update_tab = MagicMock()

    files.update_list()
    mock_window.core.assistants.get_by_id.assert_called_once()
    files.update_tab.assert_called_once()
