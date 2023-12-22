import os

import pytest
from unittest.mock import MagicMock, mock_open, patch

from PySide6.QtWidgets import QMainWindow

from pygpt_net.core.config import Config


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.config = MagicMock(spec=Config)
    window.config.path = 'test_path'
    window.app = MagicMock()
    return window


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "context_threshold":
        return 200


def test_get_user_path(mock_window):
    """
    Test get user path
    """
    config = Config(mock_window)
    config.path = 'test_path'
    assert config.get_user_path() == 'test_path'


def test_get_available_langs(mock_window):
    """
    Test get available languages
    """
    config = Config(mock_window)
    config.get_root_path = MagicMock(return_value='test_path')
    config.get_user_path = MagicMock(return_value='test_path')
    os.path.exists = MagicMock(return_value=True)
    os.listdir = MagicMock(return_value=['locale.en.ini', 'locale.de.ini', 'locale.fr.ini'])
    assert config.get_available_langs() == ['en', 'de', 'fr']

