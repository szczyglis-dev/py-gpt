from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.anims.toggles import AnimToggle


def test_anim_toggle_setup_animation_targets_checked_and_unchecked_positions():
    widget = SimpleNamespace(
        animations_group=MagicMock(),
        animation=MagicMock(),
    )

    AnimToggle.setup_animation(widget, 1)
    widget.animations_group.stop.assert_called_once_with()
    widget.animation.setEndValue.assert_called_once_with(1)
    widget.animations_group.start.assert_called_once_with()

    widget.animations_group.reset_mock()
    widget.animation.reset_mock()
    AnimToggle.setup_animation(widget, 0)
    widget.animation.setEndValue.assert_called_once_with(0)
    widget.animations_group.start.assert_called_once_with()


def test_anim_toggle_property_setters_update_state_and_repaint():
    widget = SimpleNamespace(_handle_position=0.0, _pulse_radius=0.0, update=MagicMock())

    AnimToggle.handle_position.fset(widget, 0.75)
    assert widget._handle_position == 0.75
    AnimToggle.pulse_radius.fset(widget, 12.5)
    assert widget._pulse_radius == 12.5
    assert widget.update.call_count == 2


def test_anim_toggle_property_getters_return_internal_values():
    widget = SimpleNamespace(_handle_position=0.25, _pulse_radius=8)
    assert AnimToggle.handle_position.fget(widget) == 0.25
    assert AnimToggle.pulse_radius.fget(widget) == 8
