from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.finder.finder import Finder


def _finder():
    window = MagicMock()
    input_node = MagicMock()
    counter_node = MagicMock()
    window.ui.nodes = {
        "dialog.find.input": input_node,
        "dialog.find.counter": counter_node,
    }
    window.ui.dialog = {"find": MagicMock()}
    finder = Finder(window)
    return finder, window, input_node, counter_node


def test_finder_clear_search_delegates_and_updates_counter():
    finder, _, _, _ = _finder()
    finder.parent = MagicMock()
    finder.update_counter = MagicMock()

    finder.clear_search()

    finder.parent.clear_search.assert_called_once_with()
    finder.update_counter.assert_called_once_with()


def test_finder_focus_input_searches_only_non_empty_text():
    finder, _, _, _ = _finder()
    finder.parent = MagicMock()
    finder.update_counter = MagicMock()

    finder.focus_input("needle")
    finder.parent.find.assert_called_once_with("needle")

    finder.parent.find.reset_mock()
    finder.focus_input("")
    finder.parent.find.assert_not_called()
    assert finder.update_counter.call_count == 2


def test_finder_search_navigation_and_text_changed_delegate():
    finder, _, _, _ = _finder()
    finder.parent = MagicMock()
    finder.update_counter = MagicMock()

    finder.search_text_changed("abc")
    finder.prev()
    finder.next()

    finder.parent.find.assert_called_once_with("abc")
    finder.parent.find_prev.assert_called_once_with()
    finder.parent.find_next.assert_called_once_with()
    assert finder.update_counter.call_count == 3


def test_finder_focus_in_sets_parent_and_updates_counter():
    finder, _, _, _ = _finder()
    parent = MagicMock()
    finder.set = MagicMock()
    finder.update_counter = MagicMock()

    finder.focus_in(parent)

    finder.set.assert_called_once_with(parent)
    finder.update_counter.assert_called_once_with()


def test_finder_get_search_string_reads_input_node():
    finder, _, input_node, _ = _finder()
    input_node.text.return_value = "abc"

    assert finder.get_search_string() == "abc"


def test_finder_set_and_unset_only_clear_matching_parent():
    finder, _, _, _ = _finder()
    parent = MagicMock()
    other = MagicMock()

    finder.set(parent)
    finder.unset(other)
    assert finder.parent is parent

    finder.unset(parent)
    assert finder.parent is None


def test_finder_open_prepares_parent_and_reuses_open_dialog():
    finder, window, input_node, _ = _finder()
    parent = MagicMock()
    input_node.text.return_value = "needle"

    finder.open(parent)

    parent.prepare.assert_called_once_with(clear=False)
    window.ui.dialog["find"].show.assert_called_once_with()
    input_node.setFocus.assert_called_once_with()
    parent.find.assert_called_once_with("needle")
    assert finder.opened is True

    window.ui.dialog["find"].show.reset_mock()
    parent.prepare.reset_mock()
    input_node.setFocus.reset_mock()
    finder.open(parent)
    window.ui.dialog["find"].show.assert_not_called()
    parent.prepare.assert_not_called()
    input_node.setFocus.assert_called_once_with()


def test_finder_close_can_reset_parent_or_keep_highlights():
    finder, window, _, _ = _finder()
    finder.opened = True
    finder.parent = MagicMock()

    finder.close(reset=True)
    finder.parent.reset.assert_called_once_with()
    window.ui.dialog["find"].hide.assert_called_once_with()
    assert finder.opened is False

    finder.parent.reset.reset_mock()
    finder.close(reset=False)
    finder.parent.reset.assert_not_called()


def test_finder_clear_and_clear_input_delegate_to_parent():
    finder, _, input_node, _ = _finder()
    finder.parent = MagicMock()
    finder.update_counter = MagicMock()

    finder.clear(restore=True, to_end=False)
    finder.parent.clear.assert_called_once_with(True, False)
    finder.update_counter.assert_called_once_with()

    finder.clear_input()
    input_node.clear.assert_called_once_with()
    finder.parent.find.assert_called_once_with("")


def test_finder_update_counter_handles_list_and_integer_match_models():
    finder, _, _, counter = _finder()
    finder.opened = True

    finder.parent = SimpleNamespace(matches=[1, 2, 3], current_match_index=1)
    finder.update_counter()
    counter.setText.assert_called_with("2/3")

    finder.parent = SimpleNamespace(matches=7, current_match_index=3)
    finder.update_counter()
    counter.setText.assert_called_with("3/7")

    finder.parent = SimpleNamespace(matches=[], current_match_index=-1)
    finder.update_counter()
    counter.setText.assert_called_with("0/0")


def test_finder_update_counter_is_noop_when_dialog_closed():
    finder, _, _, counter = _finder()
    finder.opened = False

    finder.update_counter()

    counter.setText.assert_not_called()
