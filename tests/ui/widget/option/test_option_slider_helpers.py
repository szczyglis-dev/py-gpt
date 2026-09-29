from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.slider import NoScrollSlider


def test_no_scroll_slider_ignores_wheel_event():
    event = MagicMock()
    NoScrollSlider.wheelEvent(SimpleNamespace(), event)
    event.ignore.assert_called_once_with()
