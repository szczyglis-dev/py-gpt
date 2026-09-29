from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.audio.bar import InputBar, OutputBar


@pytest.mark.parametrize("cls", [InputBar, OutputBar])
def test_audio_bar_set_level_updates_only_when_value_changes(cls):
    widget = SimpleNamespace(_level=10, update=MagicMock())

    cls.setLevel(widget, 10)
    widget.update.assert_not_called()

    cls.setLevel(widget, 42.5)
    assert widget._level == 42.5
    widget.update.assert_called_once_with()
