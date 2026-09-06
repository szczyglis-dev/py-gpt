from unittest.mock import MagicMock

from pygpt_net.controller.dialogs.dialogs import Dialogs


def test_dialogs_setup_delegates_to_info_controller():
    dialogs = Dialogs.__new__(Dialogs)
    dialogs.window = MagicMock()
    dialogs.info = MagicMock()
    dialogs.confirm = MagicMock()
    dialogs.debug = MagicMock()

    dialogs.setup()

    dialogs.info.setup.assert_called_once_with()
