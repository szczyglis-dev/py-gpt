#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 11:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from pygpt_net.core.filesystem import Filesystem
from tests.mocks import mock_window_conf
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.core.attachments import Attachments


def test_install():
    """
    Test install
    """
    attachments = Attachments()
    attachments.provider = MagicMock()
    attachments.provider.install = MagicMock()
    attachments.install()
    attachments.provider.install.assert_called_once_with()


def test_patch():
    """
    Test patch
    """
    attachments = Attachments()
    attachments.provider = MagicMock()
    attachments.provider.patch = MagicMock()
    version = '1.0.0'
    attachments.patch(version)
    attachments.provider.patch.assert_called_once_with(version)


def test_select():
    """
    Test select
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    attachments.select(mode, file_id)
    assert attachments.current == file_id


def test_select_not_exists():
    """
    Test select when not exists
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    attachments.select(mode, 'other_id')
    assert attachments.current is None


def test_count():
    """
    Test count
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.count(mode) == 1


def test_get_ids():
    """
    Test get ids
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.get_ids(mode) == [file_id]


def test_get_id_by_idx():
    """
    Test get id by index
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.get_id_by_idx(mode, 0) == file_id


def test_get_by_id():
    """
    Test get by id
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.get_by_id(mode, file_id) == items[mode][file_id]


def test_get_by_idx():
    """
    Test get by index
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    file_id2 = 'test_id2'

    items = {
        mode: {
            file_id: AttachmentItem(),
            file_id2: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.get_by_idx(mode, 0) == items[mode][file_id]
    assert attachments.get_by_idx(mode, 1) == items[mode][file_id2]


def test_get_all():
    """
    Test get all
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.get_all(mode) == items[mode]


def test_new():
    """
    Test new
    """
    with patch('pygpt_net.core.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        attachment = AttachmentItem()
        attachment.id = file_id
        attachment.name = name
        attachment.path = path

        attachments.create = MagicMock(return_value=attachment)
        result = attachments.new(mode, name, path, True)

        assert result == attachment
        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == name
        assert attachments.items[mode][file_id].path == path
        assert attachments.current == file_id
        mock_save.assert_called_once()


def test_build():
    """
    Test build
    """
    attachments = Attachments()
    result = attachments.build()
    assert isinstance(result, AttachmentItem)
    assert result.name is None
    assert result.path is None


def test_create():
    """
    Test create
    """
    attachment = AttachmentItem()
    attachments = Attachments()
    attachments.build = MagicMock(return_value=attachment)
    attachments.provider = MagicMock()
    attachments.provider.create = MagicMock(return_value='some_id')
    result = attachments.create()
    attachments.provider.create.assert_called_once_with(attachment)
    assert isinstance(result, AttachmentItem)
    assert result.id == 'some_id'


def test_add():
    """
    Test add
    """
    with patch('pygpt_net.core.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        item = AttachmentItem()
        item.id = file_id
        item.name = name
        item.path = path

        attachments.add(mode, item)

        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == name
        assert attachments.items[mode][file_id].path == path
        mock_save.assert_called_once()


def test_has():
    """
    Test has
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    assert not attachments.has(mode)

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.has(mode) is True


def test_has_not():
    """
    Test has
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    assert not attachments.has(mode)

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.has('test2') is False


def test_delete():
    """
    Test delete
    """
    with patch('pygpt_net.core.attachments.Attachments.save'):
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'

        items = {
            mode: {
                file_id: AttachmentItem()
            }
        }
        attachments.items = items
        attachments.delete(mode, file_id)
        assert attachments.items == {'test': {}}  # empty dict


def test_delete_all():
    """
    Test delete all
    """
    with patch('pygpt_net.core.attachments.Attachments.clear'):
        attachments = Attachments()
        attachments.clear = MagicMock()
        attachments.provider = MagicMock()
        attachments.provider.truncate = MagicMock()
        mode = 'test'
        file_id = 'test_id'

        items = {
            mode: {
                file_id: AttachmentItem()
            }
        }
        attachments.items = items
        attachments.delete_all(mode)
        attachments.clear.assert_called_once_with(mode)
        attachments.provider.truncate.assert_called_once_with(mode)


def test_clear():
    """
    Test clear
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    attachments.clear(mode)
    assert attachments.items == {'test': {}}


def test_clear_all():
    """
    Test clear all
    """
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    attachments.clear_all()
    assert attachments.items == {}


def test_replace_id():
    """
    Test replace id
    """
    with patch('pygpt_net.core.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        item = AttachmentItem()
        item.id = 'new_id'
        item.name = name
        item.path = path

        attachments.add(mode, item)
        attachments.replace_id(mode, file_id, item)

        assert attachments.items[mode]['new_id'].id == 'new_id'
        assert attachments.items[mode]['new_id'].name == name
        assert attachments.items[mode]['new_id'].path == path
        mock_save.assert_called_once()


def test_rename_file():
    """
    Test rename file
    """
    with patch('pygpt_net.core.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        item = AttachmentItem()
        item.id = file_id
        item.name = name
        item.path = path
        attachments.add(mode, item)
        attachments.get_by_id = MagicMock(return_value=item)
        attachments.rename_file(mode, file_id, 'new_name')

        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == 'new_name'
        assert attachments.items[mode][file_id].path == path


def test_make_json_list():
    """
    Test make json list
    """
    attachments = Attachments()
    file_id = 'test_id'
    name = 'test_name'
    path = 'test_path'

    items = {}
    item = AttachmentItem()
    item.id = file_id
    item.name = name
    item.path = path
    items[file_id] = item

    result = attachments.make_json_list(items)
    assert result[file_id]['name'] == name
    assert result[file_id]['path'] == path


def test_from_files():
    """
    Test from files
    """
    with patch('pygpt_net.core.attachments.Attachments.save'):
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        attachments.clear = MagicMock()
        attachments.from_files(mode, {file_id: {'name': name, 'path': path}})

        attachments.clear.assert_called_once()
        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == name
        assert attachments.items[mode][file_id].path == path


def test_from_attachments():
    """
    Test from attachments
    """
    with patch('pygpt_net.core.attachments.Attachments.save'):
        attachments = Attachments()

        mode = 'test'

        items = {}
        attachment = AttachmentItem()
        attachment.id = 'test_id'
        attachment.name = 'test_name'
        attachment.path = 'test_path'
        items['test_id'] = attachment

        attachments.clear = MagicMock()
        attachments.from_attachments(mode, items)

        assert attachments.items[mode]['test_id'].id == 'test_id'
        assert attachments.items[mode]['test_id'].name == 'test_name'
        assert attachments.items[mode]['test_id'].path == 'test_path'

        attachments.clear.assert_called_once()


def test_load(mock_window_conf):
    """
    Test load
    """
    att1 = AttachmentItem()
    att1.name = 'Attachment 1'

    att2 = AttachmentItem()
    att2.name = 'Attachment 2'
    fake_data = {
        'chat': {
            'id1': att1,
            'id2': att2,
        }
    }
    mock_window_conf.core.filesystem = Filesystem(mock_window_conf)
    attachments = Attachments(window=mock_window_conf)
    attachments.provider = {}
    attachments.provider = MagicMock()
    attachments.provider.load.return_value = fake_data
    attachments.load()

    attachments.provider.load.assert_called_once()
    assert attachments.items['chat']['id1'].name == 'Attachment 1'
    assert attachments.items['chat']['id2'].name == 'Attachment 2'


def test_save(mock_window_conf):
    """
    Test save
    """
    a1 = AttachmentItem()
    a2 = AttachmentItem()
    items = {
        'chat': {
            'attachment1': a1,
            'attachment2': a2,
        }
    }
    mock_window_conf.core.filesystem = Filesystem(mock_window_conf)
    attachments = Attachments(mock_window_conf)
    attachments.items = items
    attachments.provider = MagicMock()
    attachments.provider.patch = MagicMock()
    attachments.save()
    attachments.provider.save.assert_called_once()
