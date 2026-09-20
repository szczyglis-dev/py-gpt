from pygpt_net.core.modes.modes import Modes


class Item:
    def __init__(self, *, legacy=False, default=False):
        self.legacy = legacy
        self.default = default


def test_ordered_keys_put_legacy_modes_last_without_reordering_groups():
    modes = Modes()
    modes.items = {
        "legacy-1": Item(legacy=True),
        "regular-1": Item(),
        "legacy-2": Item(legacy=True),
        "regular-2": Item(),
    }
    assert modes.get_ordered_keys() == ("regular-1", "regular-2", "legacy-1", "legacy-2")


def test_next_and_prev_wrap_around_ordered_modes():
    modes = Modes()
    modes.items = {"a": Item(), "b": Item(), "old": Item(legacy=True)}
    assert modes.get_next("a") == "b"
    assert modes.get_next("old") == "a"
    assert modes.get_prev("a") == "old"
    assert modes.get_prev("b") == "a"


def test_default_returns_none_when_no_mode_marked_default():
    modes = Modes()
    modes.items = {"a": Item(), "b": Item()}
    assert modes.get_default() is None
