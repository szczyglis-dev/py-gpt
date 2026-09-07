from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.anims.loader import Loader, Loading


def test_loader_start_is_idempotent_and_stop_resets_state():
    widget = SimpleNamespace(started=False, animation=MagicMock())
    Loader.start_anim(widget)
    Loader.start_anim(widget)
    widget.animation.start.assert_called_once_with()
    assert widget.started is True

    Loader.stop_anim(widget)
    assert widget.started is False
    widget.animation.stop.assert_called_once_with()


def test_loader_scale_accessors_update_repaint():
    widget = SimpleNamespace(_scale=1.0, update=MagicMock())
    assert Loader.getScale(widget) == 1.0
    Loader.setScale(widget, 1.25)
    assert Loader.getScale(widget) == 1.25
    widget.update.assert_called_once_with()


def _animation():
    return MagicMock()


def test_loading_start_creates_three_staggered_animations_once():
    anims = [_animation(), _animation(), _animation()]
    widget = SimpleNamespace(started=False, initialized=False, create_animation=MagicMock(side_effect=anims))

    Loading.start_anim(widget)
    Loading.start_anim(widget)

    assert widget.create_animation.call_args_list[0].args == (b"pos1", 0)
    assert widget.create_animation.call_args_list[1].args == (b"pos2", 200)
    assert widget.create_animation.call_args_list[2].args == (b"pos3", 400)
    for anim in anims:
        anim.start.assert_called_once_with()
    assert widget.started is True
    assert widget.initialized is True


def test_loading_stop_only_stops_created_animations():
    widget = SimpleNamespace(started=True, initialized=False)
    Loading.stop_anim(widget)
    assert widget.started is False

    widget.initialized = True
    widget.anim1 = _animation(); widget.anim2 = _animation(); widget.anim3 = _animation()
    Loading.stop_anim(widget)
    widget.anim1.stop.assert_called_once_with()
    widget.anim2.stop.assert_called_once_with()
    widget.anim3.stop.assert_called_once_with()


def test_loading_position_properties_update_and_repaint():
    widget = SimpleNamespace(_pos1=0, _pos2=0, _pos3=0, update=MagicMock())
    Loading.pos1.fset(widget, 1)
    Loading.pos2.fset(widget, 2)
    Loading.pos3.fset(widget, 3)
    assert (Loading.pos1.fget(widget), Loading.pos2.fget(widget), Loading.pos3.fget(widget)) == (1, 2, 3)
    assert widget.update.call_count == 3
