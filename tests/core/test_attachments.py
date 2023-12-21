import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from pygpt_net.core.config import Config
from pygpt_net.core.attachments import Attachments, AttachmentItem


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.config = MagicMock(spec=Config)
    window.config.path = 'test_path'
    return window


def test_create_id():
    attachments = Attachments()
    assert len(attachments.create_id()) == 36  # uuid length


def test_select():
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


def test_count():
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
    attachments = Attachments()
    mode = 'test'
    file_id = 'test_id'

    items = {
        mode: {
            file_id: AttachmentItem()
        }
    }
    attachments.items = items
    assert attachments.get_by_idx(mode, 0) == items[mode][file_id]


def test_get_all():
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


def test_delete():
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


def test_clear():
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


def test_has():
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
    assert attachments.has(mode)


def test_new():
    with patch('pygpt_net.core.attachments.Attachments.save') as mock_save:
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        attachments.create_id = MagicMock(return_value=file_id)
        attachments.new(mode, name, path, True)

        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == name
        assert attachments.items[mode][file_id].path == path
        assert attachments.current == file_id
        mock_save.assert_called_once()


def test_add():
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


def test_replace_id():
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
    with patch('pygpt_net.core.attachments.Attachments.save'):
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
        attachments.rename_file(mode, file_id, 'new_name')

        assert attachments.items[mode][file_id].id == file_id
        assert attachments.items[mode][file_id].name == 'new_name'
        assert attachments.items[mode][file_id].path == path


def test_from_files():
    with patch('pygpt_net.core.attachments.Attachments.save'):
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        attachments.clear = MagicMock()
        attachments.add = MagicMock()
        attachments.from_files(mode, {file_id: {'name': name, 'path': path}})

        attachments.clear.assert_called_once()
        attachments.add.assert_called_once()


def test_from_attachments():
    with patch('pygpt_net.core.attachments.Attachments.save'):
        attachments = Attachments()
        mode = 'test'
        file_id = 'test_id'
        name = 'test_name'
        path = 'test_path'

        attachments.clear = MagicMock()
        attachments.add = MagicMock()
        attachments.from_attachments(mode, {file_id: {'name': name, 'path': path}})

        attachments.clear.assert_called_once()
        attachments.add.assert_called_once()
