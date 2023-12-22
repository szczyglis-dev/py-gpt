import json

import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from pygpt_net.core.config import Config
from pygpt_net.core.assistants import Assistants, AssistantItem


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.config = MagicMock(spec=Config)
    window.config.path = 'test_path'
    return window


def test_get_by_idx():
    """
    Test get by index
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.get_by_idx(1) == 'assistant2'


def test_get_by_id():
    """
    Test get by id
    """
    assistants = Assistants()
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }
    assistants.items = items
    assert assistants.get_by_id('assistant2') == a2


def test_get_by_id_not_found():
    """
    Test get by id not found
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.get_by_id('assistant3') is None


def test_get_all():
    """
    Test get all
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.get_all() == items


def test_has():
    """
    Test has
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.has('assistant1') == True
    assert assistants.has('assistant3') == False


def test_create():
    """
    Test create
    """
    assistants = Assistants()
    assistant = assistants.create()
    assert isinstance(assistant, AssistantItem)


def test_add():
    """
    Test add
    """
    assistant = MagicMock()
    assistant.id = "id1"

    with patch('pygpt_net.core.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.add(assistant)

        mock_save.assert_called_once_with()
        assert assistants.items['id1'] == assistant


def test_delete():
    """
    Test delete
    """
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }

    with patch('pygpt_net.core.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.items = items
        assistants.delete('assistant1')

        mock_save.assert_called_once_with()
        assert assistants.items == {'assistant2': a2}


def test_rename_file():
    """
    Test rename file
    """
    assistant = MagicMock()
    assistant.files = {
        'file1': {'name': 'file1'},
        'file2': {'name': 'file2'},
    }
    assistant.attachments = {
        'file1': MagicMock(),
        'file2': MagicMock(),
    }

    with patch('pygpt_net.core.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.rename_file(assistant, 'file1', 'new_name')

        mock_save.assert_called_once_with()
        assert assistant.files['file1']['name'] == 'new_name'
        assert assistant.attachments['file1'].name == 'new_name'


def test_replace_attachment():
    """
    Test replace attachment
    """
    assistant = MagicMock()
    assistant.attachments = {
        'id_old': MagicMock(),
        'id_other': MagicMock(),
    }

    with patch('pygpt_net.core.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.replace_attachment(assistant, MagicMock(), 'id_old', 'id_new')

        mock_save.assert_called_once_with()
        assert 'id_old' not in assistant.attachments
        assert 'id_new' in assistant.attachments
        assert 'id_other' in assistant.attachments


def test_get_default_assistant_empty():
    """
    Test get default assistant empty
    """
    assistants = Assistants()
    assert assistants.get_default_assistant() is None


def test_get_default_assistant():
    """
    Test get default assistant
    """
    assistants = Assistants()
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }
    assistants.items = items
    assert assistants.get_default_assistant() == 'assistant1'


def test_get_file_id_by_idx():
    """
    Test get file id by index
    """
    assistants = Assistants()
    assistant = MagicMock()
    assistant.files = {
        'file1': {'name': 'file1'},
        'file2': {'name': 'file2'},
    }
    assistants.get_by_id = MagicMock(return_value=assistant)
    assert assistants.get_file_id_by_idx(assistant, 1) == 'file2'


def test_get_file_id_by_idx_not_found():
    """
    Test get file id by index not found
    """
    assistants = Assistants()
    assistant = MagicMock()
    assistant.files = {
        'file1': {'name': 'file1'},
        'file2': {'name': 'file2'},
    }
    assistants.get_by_id = MagicMock(return_value=assistant)
    assert assistants.get_file_id_by_idx(assistant, 2) is None


def test_get_file_by_id():
    """
    Test get file by id
    """
    assistants = Assistants()
    assistant = MagicMock()
    assistant.files = {
        'file1': {'name': 'file1'},
        'file2': {'name': 'file2'},
    }
    assistants.get_by_id = MagicMock(return_value=assistant)
    assert assistants.get_file_by_id(assistant, 'file1') == {'name': 'file1'}


def test_get_file_by_id_not_found():
    """
    Test get file by id not found
    """
    assistants = Assistants()
    assistant = MagicMock()
    assistant.files = {
        'file1': {'name': 'file1'},
        'file2': {'name': 'file2'},
    }
    assistants.get_by_id = MagicMock(return_value=assistant)
    assert assistants.get_file_by_id(assistant, 'file3') is None


def test_import_files(mock_window):
    """
    Test import files
    """
    with patch('pygpt_net.core.assistants.Assistants.import_filenames') as mock_import:
        mock_import.return_value = 'remote_name'

        files = []
        file1 = MagicMock()
        file1.id = 'file1'
        file1.name = ''
        files.append(file1)

        assistants = Assistants(window=mock_window)
        assistant = MagicMock()
        assistant.files = {
            'file1': {'id': 'file1', 'name': 'file1', 'path': ''},
            'file2': {'id': 'file2', 'name': 'file2', 'path': ''},  # should be removed
        }
        assistants.get_by_id = MagicMock(return_value=assistant)
        assistants.import_files(assistant, files)
        assert assistant.files == {'file1': {'id': 'file1', 'name': 'file1', 'path': ''}}


def test_import_files_with_remote_name(mock_window):
    """
    Test import files with remote name
    """
    with patch('pygpt_net.core.assistants.Assistants.import_filenames') as mock_import:
        mock_import.return_value = 'remote_name'

        files = []
        file1 = MagicMock()
        file1.id = 'file1'
        file1.name = 'remote_name'
        files.append(file1)

        assistants = Assistants(window=mock_window)
        assistant = MagicMock()
        assistant.files = {
            'file1': {'id': 'file1', '': 'file1', 'path': ''},  # should be updated
            'file2': {'id': 'file2', '': 'file2', 'path': ''},
        }
        assistants.get_by_id = MagicMock(return_value=assistant)
        assistants.import_files(assistant, files)
        assert assistant.files == {'file1': {'id': 'file1', 'name': 'remote_name', 'path': ''}}


def test_import_filenames(mock_window):
    """
    Test import filenames
    """
    fake_file_info = MagicMock()
    fake_file_info.filename = 'fake.txt'

    assistants = Assistants(window=mock_window)
    app = MagicMock()
    app.gpt_assistants = MagicMock()
    app.gpt_assistants.file_info = MagicMock(return_value=fake_file_info)
    assistants.window.app = app
    filename = assistants.import_filenames('some_id')

    assert filename == 'fake.txt'


def test_load_method(mock_window):
    """
    Test load method
    """
    fake_data = {'items': {'id1': {'name': 'Assistant 1'}, 'id2': {'name': 'Assistant 2'}}}
    fake_json_data = json.dumps(fake_data)
    fake_file = mock_open(read_data=fake_json_data)

    with patch('os.path.exists', return_value=True), \
            patch('json.load', return_value=fake_data), \
            patch('builtins.open', fake_file):
        assistants = Assistants(window=mock_window)
        assistants.load()

        assert assistants.items['id1'].name == 'Assistant 1'
        assert assistants.items['id2'].name == 'Assistant 2'
