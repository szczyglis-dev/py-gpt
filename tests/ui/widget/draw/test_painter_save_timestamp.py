from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.widget.draw.painter import PainterWidget


def test_painter_save_default_filename_uses_mocked_clock_not_host_timezone():
    widget = SimpleNamespace(_ensure_composited_image=MagicMock(), image=MagicMock())
    fixed = datetime(2026, 9, 7, 2, 5, 9)

    with patch("pygpt_net.ui.widget.draw.painter.datetime.datetime") as dt_cls, \
         patch("pygpt_net.ui.widget.draw.painter.QFileDialog.getSaveFileName", return_value=("/tmp/out.png", "PNG"), create=True) as save_dialog:
        dt_cls.now.return_value = fixed
        PainterWidget.action_save(widget)

    save_dialog.assert_called_once_with(
        widget,
        "Save Image",
        "2026-09-07_02-05-09.png",
        "PNG(*.png);;JPEG(*.jpg *.jpeg);;All Files(*.*) ",
    )
    widget.image.save.assert_called_once_with("/tmp/out.png")


def test_painter_save_cancel_does_not_write_image():
    widget = SimpleNamespace(_ensure_composited_image=MagicMock(), image=MagicMock())
    with patch("pygpt_net.ui.widget.draw.painter.QFileDialog.getSaveFileName", return_value=("", ""), create=True):
        PainterWidget.action_save(widget)
    widget.image.save.assert_not_called()
