#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 03:00:00                  #
# ================================================== #

import os
from unittest.mock import MagicMock, patch

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem
from tests.mocks import mock_window
from pygpt_net.controller import Attachment


def test_setup(mock_window):
    """Test setup attachment"""
    attachment = Attachment(mock_window)
    mock_window.core.config.data['attachments_send_clear'] = True
    mock_window.core.config.data['attachments_capture_clear'] = True
    mock_window.ui.nodes['attachments.send_clear'] = MagicMock()
    mock_window.ui.nodes['attachments.capture_clear'] = MagicMock()
    mock_window.core.attachments.load = MagicMock()
    attachment.update = MagicMock()
    attachment.setup()
    mock_window.ui.nodes['attachments.send_clear'].setChecked.assert_called()
    mock_window.ui.nodes['attachments.capture_clear'].setChecked.assert_called()
    mock_window.core.attachments.load.assert_called_once()
    attachment.update.assert_called_once()


def test_update_has(mock_window):
    """Test update attachment"""
    attachment = Attachment(mock_window)
    mock_window.core.config.data['mode'] = 'vision'
    mock_window.core.config.data['attachments_send_clear'] = True
    mock_window.core.config.data['attachments_capture_clear'] = True
    mock_window.ui.chat.input.attachments.update = MagicMock()
    mock_window.core.attachments.get_all = MagicMock()
    mock_window.controller.chat.vision.available = MagicMock()
    mock_window.controller.chat.vision.unavailable = MagicMock()
    attachment.update_tab = MagicMock()
    attachment.has = MagicMock(return_value=True)
    attachment.update()
    mock_window.ui.chat.input.attachments.update.assert_called_once()
    mock_window.core.attachments.get_all.assert_called_once()
    mock_window.controller.chat.vision.available.assert_called_once()
    mock_window.controller.chat.vision.unavailable.assert_not_called()


def test_update_empty(mock_window):
    """Test update attachment"""
    attachment = Attachment(mock_window)
    mock_window.core.config.data['mode'] = 'vision'
    mock_window.core.config.data['attachments_send_clear'] = True
    mock_window.core.config.data['attachments_capture_clear'] = True
    mock_window.ui.chat.input.attachments.update = MagicMock()
    mock_window.core.attachments.get_all = MagicMock()
    mock_window.controller.chat.vision.available = MagicMock()
    mock_window.controller.chat.vision.unavailable = MagicMock()
    attachment.update_tab = MagicMock()
    attachment.has = MagicMock(return_value=False)
    attachment.update()
    mock_window.ui.chat.input.attachments.update.assert_called_once()
    mock_window.core.attachments.get_all.assert_called_once()
    mock_window.controller.chat.vision.available.assert_not_called()
    mock_window.controller.chat.vision.unavailable.assert_called()


def test_update_tab(mock_window):
    """Test update tab"""
    attachment = Attachment(mock_window)
    mock_window.core.config.data['mode'] = 'vision'
    mock_window.core.attachments.count = MagicMock(return_value=1)
    mock_window.ui.tabs['input'].setTabText = MagicMock()
    attachment.update_tab('vision')
    mock_window.core.attachments.count.assert_called_once()
    mock_window.ui.tabs['input'].setTabText.assert_called_once()


def test_select(mock_window):
    """Test select attachment"""
    attachment = Attachment(mock_window)
    mock_window.core.attachments.get_id_by_idx = MagicMock(return_value=1)
    mock_window.core.attachments.current = 0
    attachment.select('vision', 1)
    mock_window.core.attachments.get_id_by_idx.assert_called_once()
    assert mock_window.core.attachments.current == 1


def test_delete(mock_window):
    """Test delete attachment"""
    attachment = Attachment(mock_window)
    mock_window.core.attachments.get_id_by_idx = MagicMock(return_value=1)
    mock_window.core.attachments.current = 0
    mock_window.core.attachments.delete = MagicMock()
    mock_window.core.attachments.current = 1
    attachment.update = MagicMock()
    attachment.delete(1, True)
    mock_window.core.attachments.get_id_by_idx.assert_called_once()
    mock_window.core.attachments.delete.assert_called_once()
    assert mock_window.core.attachments.current is None
    attachment.update.assert_called_once()


def test_rename(mock_window):
    """Test rename attachment"""
    attachment = Attachment(mock_window)
    mock_window.core.attachments.get_id_by_idx = MagicMock(return_value=1)
    mock_window.core.attachments.current = 0
    mock_window.core.attachments.rename = MagicMock()
    mock_window.core.attachments.current = 1
    mock_window.ui.dialog['rename'] = MagicMock()
    attachment.update = MagicMock()

    attachment.rename('vision', 1)
    mock_window.core.attachments.get_id_by_idx.assert_called_once_with('vision', 1)
    mock_window.ui.dialog['rename'].id = 'attachment'
    mock_window.ui.dialog['rename'].input.setText.assert_called_once()
    mock_window.ui.dialog['rename'].show.assert_called_once()


def test_update_name(mock_window):
    """Test update name"""
    attachment = Attachment(mock_window)
    mock_window.core.attachments.get_id_by_idx = MagicMock(return_value=1)
    mock_window.core.attachments.current = 0
    mock_window.core.attachments.rename_file = MagicMock()
    mock_window.core.attachments.current = 1
    mock_window.core.config.get = MagicMock(return_value='assistant')
    mock_window.controller.assistant.files.update_name = MagicMock()
    mock_window.ui.dialog['rename'] = MagicMock()
    attachment.update = MagicMock()

    attachment.update_name('1', 'test')
    mock_window.core.attachments.rename_file.assert_called_once()
    mock_window.controller.assistant.files.update_name.assert_called_once()
    mock_window.ui.dialog['rename'].close.assert_called_once()
    attachment.update.assert_called_once()


def test_add(mock_window):
    """Test add attachment"""
    item = AttachmentItem()
    attachment = Attachment(mock_window)
    mock_window.core.attachments.add = MagicMock()
    attachment.update = MagicMock()
    attachment.add('vision', item)
    mock_window.core.attachments.add.assert_called_once()
    attachment.update.assert_called_once()


def test_clear_vision(mock_window):
    """Test clear attachments list: vision"""
    attachment = Attachment(mock_window)
    mock_window.core.config.data['mode'] = 'vision'

    mock_window.core.attachments.delete_all = MagicMock()
    mock_window.controller.chat.vision.unavailable = MagicMock()
    mock_window.controller.assistant.files.clear_attachments = MagicMock()
    attachment.update = MagicMock()
    attachment.clear(force=True)
    mock_window.core.attachments.delete_all.assert_called_once_with('vision')
    mock_window.controller.chat.vision.unavailable.assert_called_once()
    attachment.update.assert_called_once()


def test_clear_assistant(mock_window):
    """Test clear attachments list: assistant"""
    attachment = Attachment(mock_window)
    mock_window.core.config.data['mode'] = 'assistant'
    mock_window.core.config.data['assistant'] = 'test'

    ass = AssistantItem()
    mock_window.core.assistants.get_by_id = MagicMock(return_value=ass)
    mock_window.controller.assistant.files.clear_attachments = MagicMock()

    mock_window.core.attachments.delete_all = MagicMock()
    mock_window.controller.chat.vision.unavailable = MagicMock()
    mock_window.controller.assistant.files.clear_attachments = MagicMock()
    attachment.update = MagicMock()
    attachment.clear(force=True)
    mock_window.core.attachments.delete_all.assert_called_once_with('assistant')
    mock_window.controller.chat.vision.unavailable.assert_called_once()
    mock_window.controller.assistant.files.clear_attachments.assert_called_once()
    attachment.update.assert_called_once()


def test_open_dir(mock_window):
    attachment = Attachment(mock_window)
    att = AttachmentItem
    att.path = "path"
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value=True
        mock_window.controller.files.open_in_file_manager = MagicMock()
        mock_window.core.attachments.get_by_id = MagicMock(return_value=att)
        attachment.open_dir('assistant', 1)
        mock_window.controller.files.open_in_file_manager.assert_called_once()


def test_open(mock_window):
    attachment = Attachment(mock_window)
    att = AttachmentItem
    att.path = "path"
    with patch('os.path.exists') as os_path_exists:
        os_path_exists.return_value=True
        mock_window.controller.files.open = MagicMock()
        mock_window.core.attachments.get_by_id = MagicMock(return_value=att)
        attachment.open('assistant', 1)
        mock_window.controller.files.open.assert_called_once()


def test_import_from_assistant(mock_window):
    attachment = Attachment(mock_window)
    assistant = AssistantItem()
    assistant.attachments = []
    mock_window.core.attachments.from_attachments = MagicMock()
    attachment.import_from_assistant('assistant', assistant)
    mock_window.core.attachments.from_attachments.assert_called_once()


def test_has(mock_window):
    attachment = Attachment(mock_window)
    mock_window.core.attachments.has = MagicMock(return_value=True)
    assert attachment.has('assistant') is True
    mock_window.core.attachments.has.assert_called_once_with('assistant')


def test_download(mock_window):
    attachment = Attachment(mock_window)
    data = MagicMock()
    data.filename = 'test'
    mock_window.core.gpt.assistants.file_info = MagicMock(return_value=data)

    with patch('os.path.join') as os_path_join, \
        patch('os.path.exists') as os_path_exists:

        os_path_join.return_value='path'
        os_path_exists.return_value=True

        mock_window.core.attachments.download = MagicMock()
        result = attachment.download('file_id')
        mock_window.core.gpt.assistants.file_download.assert_called_once_with('file_id', 'path')
        assert result == 'path'


def test_toggle_send_clear(mock_window):
    attachment = Attachment(mock_window)
    mock_window.core.config.set = MagicMock()
    attachment.toggle_send_clear(True)
    mock_window.core.config.set.assert_called_once_with('attachments_send_clear', True)


def test_toggle_capture_clear(mock_window):
    attachment = Attachment(mock_window)
    mock_window.core.config.set = MagicMock()
    attachment.toggle_capture_clear(True)
    mock_window.core.config.set.assert_called_once_with('attachments_capture_clear', True)


def test_is_capture_clear(mock_window):
    attachment = Attachment(mock_window)
    mock_window.core.config.has = MagicMock(return_value=True)
    mock_window.core.config.get = MagicMock(return_value=True)
    assert attachment.is_capture_clear() is True
    mock_window.core.config.has.assert_called_once_with('attachments_capture_clear')
    mock_window.core.config.get.assert_called_once_with('attachments_capture_clear')


def test_is_send_clear(mock_window):
    attachment = Attachment(mock_window)
    mock_window.core.config.has = MagicMock(return_value=True)
    mock_window.core.config.get = MagicMock(return_value=True)
    assert attachment.is_send_clear() is True
    mock_window.core.config.has.assert_called_once_with('attachments_send_clear')
    mock_window.core.config.get.assert_called_once_with('attachments_send_clear')
