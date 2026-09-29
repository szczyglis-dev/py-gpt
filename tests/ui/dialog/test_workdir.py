from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.workdir import Workdir


def _widget():
    info = MagicMock()
    status = MagicMock()
    config = MagicMock()
    config.get_user_path.return_value = "/work/current"
    filesystem = MagicMock()
    filesystem.get_directory_size.return_value = "12 MB"
    window = SimpleNamespace(
        ui=SimpleNamespace(nodes={"workdir.change.info": info, "workdir.change.status": status}),
        core=SimpleNamespace(config=config, filesystem=filesystem),
        controller=MagicMock(),
    )
    path = MagicMock()
    return SimpleNamespace(window=window, path=path), info, status


def test_prepare_uses_current_directory_size_and_processes_events():
    widget, info, _ = _widget()

    with patch("pygpt_net.ui.dialog.workdir.trans", return_value="Need {size}"), \
            patch("pygpt_net.ui.dialog.workdir.QApplication.processEvents") as process_events:
        Workdir.prepare(widget)

    widget.window.core.filesystem.get_directory_size.assert_called_once_with("/work/current")
    info.setText.assert_called_once_with("Need 12 MB")
    process_events.assert_called_once()


def test_show_and_hide_status_update_label_and_process_events():
    widget, _, status = _widget()

    with patch("pygpt_net.ui.dialog.workdir.QApplication.processEvents") as process_events:
        Workdir.show_status(widget, "Migrating")
        Workdir.hide_status(widget)

    assert status.setText.call_args_list[0].args == ("Migrating",)
    assert status.setVisible.call_args_list[0].args == (True,)
    assert status.setText.call_args_list[1].args == ("",)
    assert status.setVisible.call_args_list[1].args == (False,)
    assert process_events.call_count == 2


def test_change_directory_migrates_text_from_path_widget():
    widget, _, _ = _widget()
    widget.path.text.return_value = "/work/new"

    Workdir.change_directory(widget)

    widget.window.controller.settings.workdir.migrate.assert_called_once_with("/work/new")


def test_reset_directory_restores_configured_path_and_value():
    widget, _, _ = _widget()

    with patch("pygpt_net.ui.dialog.workdir.QApplication.processEvents"):
        Workdir.reset_directory(widget)

    assert widget.path.value == "/work/current"
    widget.path.setText.assert_called_once_with("/work/current")


def test_set_path_updates_text_value_and_widget():
    widget, _, _ = _widget()

    with patch("pygpt_net.ui.dialog.workdir.QApplication.processEvents"):
        Workdir.set_path(widget, "/work/other")

    widget.path.setText.assert_called_once_with("/work/other")
    assert widget.path.value == "/work/other"
    widget.path.update.assert_called_once()
