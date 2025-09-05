#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.filesystem import Filesystem
from tests.mocks import mock_window_conf
from pygpt_net.core.attachments import Attachments


def _make_item(id=None, name=None, path=None):
    obj = SimpleNamespace()
    obj.id = id
    obj.name = name
    obj.path = path
    obj.consumed = False

    def serialize():
        return {
            'id': id,
            'uuid': None,
            'name': name,
            'path': path,
            'size': 0,
            'remote': None,
            'ctx': False,
            'vector_store_ids': [],
            'type': 'file',
            'extra': {},
            'meta_id': None,
            'send': False,
        }

    obj.serialize = serialize
    return obj


class FakeAttachmentItem:
    TYPE_FILE = 'file'
    TYPE_URL = 'url'

    def __init__(self):
        self.name = None
        self.id = None
        self.uuid = None
        self.path = None
        self.remote = None
        self.vector_store_ids = []
        self.meta_id = None
        self.ctx = False
        self.consumed = False
        self.size = 0
        self.send = False
        self.type = self.TYPE_FILE
        self.extra = {}

    def serialize(self) -> dict:
        return {
            'id': self.id,
            'uuid': str(self.uuid) if self.uuid is not None else None,
            'name': self.name,
            'path': self.path,
            'size': self.size,
            'remote': self.remote,
            'ctx': self.ctx,
            'vector_store_ids': self.vector_store_ids,
            'type': self.type,
            'extra': self.extra,
            'meta_id': self.meta_id,
            'send': self.send,
        }


def test_install():
    attachments = Attachments()
    attachments.provider = MagicMock()
    attachments.provider.install = MagicMock()
    attachments.install()
    attachments.provider.install.assert_called_once_with()


def test_patch():
    attachments = Attachments()
    attachments.provider = MagicMock()
    attachments.provider.patch = MagicMock()
    version = '1.0.0'
    attachments.patch(version)
    attachments.provider.patch.assert_called_once_with(version)


def test_select():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    attachments.select(mode, file_id)
    assert attachments.current == file_id


def test_select_not_exists():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    attachments.select(mode, 'other_id')
    assert attachments.current is None


def test_count():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.count(mode) == 1


def test_get_ids():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.get_ids(mode) == [file_id]


def test_get_id_by_idx():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.get_id_by_idx(mode, 0) == file_id


def test_get_by_id():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.get_by_id(mode, file_id) == items[mode][file_id]


def test_get_by_idx():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    file_id2 = 'test_id2'
    items = {mode: {file_id: _make_item(), file_id2: _make_item()}}
    attachments.items = items
    assert attachments.get_by_idx(mode, 0) == items[mode][file_id]
    assert attachments.get_by_idx(mode, 1) == items[mode][file_id2]


def test_get_all():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.get_all(mode) == items[mode]


def test_new():
    with patch('pygpt_net.core.attachments.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        attachments.window = MagicMock()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'
        attachment = _make_item(id=file_id, name=name)
        attachments.create = MagicMock(return_value=attachment)
        result = attachments.new(mode, name, path, True)
        assert result == attachment
        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == name
        assert attachments.items[mode][file_id].path == path
        assert attachments.current == file_id
        mock_save.assert_called_once()


def test_create():
    attachment = _make_item()
    attachments = Attachments()
    attachments.build = MagicMock(return_value=attachment)
    attachments.provider = MagicMock()
    attachments.provider.create = MagicMock(return_value='some_id')
    result = attachments.create()
    attachments.provider.create.assert_called_once_with(attachment)
    assert result.id == 'some_id'


def test_add():
    with patch('pygpt_net.core.attachments.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'
        item = _make_item(id=file_id, name=name, path=path)
        attachments.add(mode, item)
        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == name
        assert attachments.items[mode][file_id].path == path
        mock_save.assert_called_once()


def test_has():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    assert not attachments.has(mode)
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.has(mode) is True


def test_has_not():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    assert not attachments.has(mode)
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    assert attachments.has('test2') is False


def test_delete():
    with patch('pygpt_net.core.attachments.attachments.Attachments.save'):
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        items = {mode: {file_id: _make_item()}}
        attachments.items = items
        attachments.delete(mode, file_id)
        assert attachments.items == {'test': {}}


def test_delete_all():
    with patch('pygpt_net.core.attachments.attachments.Attachments.clear'):
        attachments = Attachments()
        attachments.window = MagicMock()
        attachments.clear = MagicMock()
        attachments.provider = MagicMock()
        attachments.provider.truncate = MagicMock()
        mode = 'test'
        file_id = 'test_id'
        items = {mode: {file_id: _make_item()}}
        attachments.items = items
        attachments.delete_all(mode)


def test_clear():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    attachments.clear(mode)
    assert attachments.items == {'test': {}}


def test_clear_all():
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'
    items = {mode: {file_id: _make_item()}}
    attachments.items = items
    attachments.clear_all()
    assert attachments.items == {}


def test_replace_id():
    with patch('pygpt_net.core.attachments.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'
        item = _make_item(id='new_id', name=name, path=path)
        attachments.add(mode, item)
        attachments.replace_id(mode, file_id, item)
        assert attachments.items[mode]['new_id'].id == 'new_id'
        assert attachments.items[mode]['new_id'].name == name
        assert attachments.items[mode]['new_id'].path == path
        mock_save.assert_called_once()


def test_rename_file():
    with patch('pygpt_net.core.attachments.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'
        item = _make_item(id=file_id, name=name, path=path)
        attachments.add(mode, item)
        attachments.get_by_id = MagicMock(return_value=item)
        attachments.rename_file(mode, file_id, 'new_name')
        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == 'new_name'
        assert attachments.items[mode][file_id].path == path
        mock_save.assert_called()


def test_make_json_list():
    attachments = Attachments()
    file_id = 'test_id'
    name = 'test_name'
    path = 'test_path'
    items = {file_id: _make_item(id=file_id, name=name, path=path)}
    result = attachments.make_json_list(items)
    assert result[file_id]['name'] == name
    assert result[file_id]['path'] == path


def test_from_attachments():
    with patch('pygpt_net.core.attachments.attachments.Attachments.save'):
        attachments = Attachments()
        mode = 'test'
        items = {}
        attachment = _make_item(id='test_id', name='test_name', path='test_path')
        items['test_id'] = attachment
        attachments.clear = MagicMock()
        attachments.from_attachments(mode, items)
        assert attachments.items[mode]['test_id'].id == 'test_id'
        assert attachments.items[mode]['test_id'].name == 'test_name'
        assert attachments.items[mode]['test_id'].path == 'test_path'
        attachments.clear.assert_called_once()


def test_load(mock_window_conf):
    att1 = _make_item(id='id1', name='Attachment 1')
    att2 = _make_item(id='id2', name='Attachment 2')
    fake_data = {
        'chat': {
            'id1': att1,
            'id2': att2,
        }
    }
    mock_window_conf.core.filesystem = Filesystem(mock_window_conf)
    attachments = Attachments(window=mock_window_conf)
    attachments.provider = MagicMock()
    attachments.provider.load.return_value = fake_data
    attachments.load()
    attachments.provider.load.assert_called_once()
    assert attachments.items['chat']['id1'].name == 'Attachment 1'
    assert attachments.items['chat']['id2'].name == 'Attachment 2'


def test_save(mock_window_conf):
    a1 = _make_item(id='attachment1', name='a1')
    a2 = _make_item(id='attachment2', name='a2')
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