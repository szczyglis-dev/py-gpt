from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.lists.profile import ProfileList


def _widget(row=2):
    index = MagicMock(); index.row.return_value = row
    profile = SimpleNamespace(
        select_by_idx=MagicMock(), duplicate_by_idx=MagicMock(), reset_by_idx=MagicMock(),
        delete_by_idx=MagicMock(), delete_all_by_idx=MagicMock(), edit_by_idx=MagicMock(),
    )
    return SimpleNamespace(
        window=SimpleNamespace(controller=SimpleNamespace(settings=SimpleNamespace(profile=profile))),
        indexAt=MagicMock(return_value=index),
    )


def test_profile_selection_helpers_sort_and_are_exception_safe():
    sm = MagicMock(); a = MagicMock(); b = MagicMock(); a.row.return_value = 8; b.row.return_value = 2
    sm.selectedRows.return_value = [a, b]
    widget = SimpleNamespace(selectionModel=lambda: sm)
    assert ProfileList._selected_rows(widget) == [8, 2]
    assert ProfileList._has_multi_selection(widget) is True
    bad = SimpleNamespace(selectionModel=MagicMock(side_effect=RuntimeError()))
    assert ProfileList._selected_rows(bad) == []
    assert ProfileList._has_multi_selection(bad) is False


@pytest.mark.parametrize("method,target", [
    (ProfileList.action_use, "select_by_idx"),
    (ProfileList.action_duplicate, "duplicate_by_idx"),
    (ProfileList.action_reset, "reset_by_idx"),
    (ProfileList.action_delete, "delete_by_idx"),
    (ProfileList.action_delete_all, "delete_all_by_idx"),
    (ProfileList.action_edit, "edit_by_idx"),
])
def test_profile_single_actions_dispatch_row(method, target):
    widget = _widget(4)
    method(widget, MagicMock())
    getattr(widget.window.controller.settings.profile, target).assert_called_once_with(4)


@pytest.mark.parametrize("method,target", [
    (ProfileList._action_reset_multi, "reset_by_idx"),
    (ProfileList._action_delete_multi, "delete_by_idx"),
    (ProfileList._action_delete_all_multi, "delete_all_by_idx"),
])
def test_profile_multi_actions_pass_lists_and_ignore_empty(method, target):
    widget = _widget()
    method(widget, [5, 1])
    getattr(widget.window.controller.settings.profile, target).assert_called_once_with([5, 1])
    getattr(widget.window.controller.settings.profile, target).reset_mock()
    method(widget, [])
    getattr(widget.window.controller.settings.profile, target).assert_not_called()
