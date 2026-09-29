from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.image.display import ImageLabel


def test_image_label_resolves_nested_main_window():
    main = object()
    wrapper = SimpleNamespace(window=main)
    assert ImageLabel._get_window(SimpleNamespace(window=wrapper)) is main
    assert ImageLabel._get_window(SimpleNamespace(window=main)) is main
    assert ImageLabel._get_window(SimpleNamespace(window=None)) is None


def test_image_actions_delegate_to_viewer():
    viewer = MagicMock()
    win = SimpleNamespace(tools={"viewer": viewer})
    widget = SimpleNamespace(path="/tmp/image.png", _get_window=lambda: win)

    ImageLabel.action_open(widget, None)
    ImageLabel.action_open_dir(widget, None)
    ImageLabel.action_save(widget, None)
    ImageLabel.action_delete(widget, None)

    viewer.open.assert_called_once_with("/tmp/image.png")
    viewer.open_dir.assert_called_once_with("/tmp/image.png")
    viewer.save.assert_called_once_with("/tmp/image.png")
    viewer.delete.assert_called_once_with("/tmp/image.png")
