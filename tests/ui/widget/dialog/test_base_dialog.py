from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QRect

from pygpt_net.ui.widget.dialog.base import BaseDialog


def test_dialog_id_prefers_shared_id():
    assert BaseDialog._get_id(SimpleNamespace(shared_id="shared", id="own")) == "shared"
    assert BaseDialog._get_id(SimpleNamespace(shared_id=None, id="own")) == "own"


def test_geometry_store_requires_flag_window_id_and_enabled_config():
    config = MagicMock()
    config.has.return_value = True
    config.get.return_value = True
    widget = SimpleNamespace(
        disable_geometry_store=False,
        window=SimpleNamespace(core=SimpleNamespace(config=config)),
        shared_id=None,
        id="dlg",
    )
    widget._get_id = lambda: BaseDialog._get_id(widget)

    assert BaseDialog.store_geometry_enabled(widget) is True
    widget.disable_geometry_store = True
    assert BaseDialog.store_geometry_enabled(widget) is False


def test_save_geometry_uses_session_storage_when_enabled():
    config = MagicMock()
    config.get_session.return_value = {"other": {}}
    widget = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(config=config)),
        size=lambda: SimpleNamespace(width=lambda: 640, height=lambda: 480),
        pos=lambda: SimpleNamespace(x=lambda: 10, y=lambda: 20),
        _get_id=lambda: "dlg",
        store_geometry_enabled=lambda: True,
    )

    BaseDialog.save_geometry(widget)

    config.set_session.assert_called_once_with(
        "layout.dialog.geometry",
        {"other": {}, "dlg": {"size": [640, 480], "pos": [10, 20]}},
    )


def test_restore_geometry_clamps_size_and_position_to_screen():
    config = MagicMock()
    config.get_session.return_value = {"dlg": {"size": [1200, 900], "pos": [-50, 9999]}}
    screen = MagicMock()
    screen.availableGeometry.return_value = QRect(0, 0, 800, 600)
    widget = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(config=config)),
        _get_id=lambda: "dlg",
        store_geometry_enabled=lambda: True,
        resize=MagicMock(),
        move=MagicMock(),
    )

    with patch("pygpt_net.ui.widget.dialog.base.QApplication.primaryScreen", return_value=screen):
        BaseDialog.restore_geometry(widget)

    size = widget.resize.call_args.args[0]
    pos = widget.move.call_args.args[0]
    assert (size.width(), size.height()) == (780, 580)
    assert pos.x() == 0
    assert pos.y() == 19
