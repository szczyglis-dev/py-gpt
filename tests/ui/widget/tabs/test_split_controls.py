from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.controller.tabs.split import TabSplit
from pygpt_net.ui.widget.tabs.output import OutputTabs


def test_split_controls_follow_enabled_column():
    """Check control routing without windows, geometry or animations."""
    buttons = [MagicMock(), MagicMock()]
    for button in buttons:
        button.parentWidget.return_value.layout.return_value.count.return_value = 0
    controller = TabSplit()
    controller.window = SimpleNamespace(ui=SimpleNamespace(
        nodes={f'layout.split.button.{i}': button for i, button in enumerate(buttons)},
        splitters={},
    ))
    for state in (False, True, False):
        controller.is_split_screen_enabled = lambda: state
        controller.sync_split_buttons()
        buttons[0].setVisible.assert_called_with(not state)
        buttons[1].setVisible.assert_called_with(state)


def test_split_controls_keep_right_corner_when_add_button_moves():
    button, controls, split_button = MagicMock(), MagicMock(), MagicMock()
    split_button.isHidden.return_value = False
    tabs = SimpleNamespace(
        cornerWidget=MagicMock(return_value=button), setCornerWidget=MagicMock(),
        corner_layout=MagicMock(), corner_controls=controls, split_button=split_button,
    )
    for corner in (Qt.TopRightCorner, None, Qt.TopLeftCorner):
        tabs.setCornerWidget.reset_mock()
        OutputTabs.place_add_button(tabs, button, corner)
        tabs.corner_layout.removeWidget.assert_called_with(button)
        controls.setVisible.assert_called_with(True)
        # Moving [+] must never replace the split controls in the right corner.
        assert all(call.args[1] == Qt.TopLeftCorner
                   for call in tabs.setCornerWidget.call_args_list)
        if corner == Qt.TopRightCorner:
            button.setParent.assert_called_with(controls)
            tabs.corner_layout.insertWidget.assert_called_with(0, button)
        elif corner is None:
            button.hide.assert_called()
        else:
            tabs.setCornerWidget.assert_called_with(button, Qt.TopLeftCorner)


def test_split_screen_public_actions_route_to_shared_transition():
    controller = TabSplit()
    controller.set_split_screen = MagicMock()
    controller.enable_split_screen(update_switch=True)
    controller.set_split_screen.assert_called_with(True, update_switch=True)
    controller.disable_split_screen()
    controller.set_split_screen.assert_called_with(False)
