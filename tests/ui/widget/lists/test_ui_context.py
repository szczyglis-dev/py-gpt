from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.lists.context import ContextList, ImportantItemDelegate


def _ctx(**overrides):
    controller = SimpleNamespace(
        ctx=SimpleNamespace(
            load=MagicMock(),
            rename=MagicMock(),
            set_important=MagicMock(),
            set_label=MagicMock(),
            delete=MagicMock(),
            new_in_group=MagicMock(),
            rename_group=MagicMock(),
            delete_group=MagicMock(),
            delete_group_all=MagicMock(),
            common=SimpleNamespace(
                duplicate=MagicMock(),
                copy_id=MagicMock(),
                reset=MagicMock(),
            ),
        ),
        idx=SimpleNamespace(indexer=SimpleNamespace(
            index_ctx_meta=MagicMock(),
            index_ctx_meta_remove=MagicMock(),
        )),
    )
    cfg = SimpleNamespace(get=MagicMock(return_value=[]), set=MagicMock(), save=MagicMock())
    values = dict(
        window=SimpleNamespace(controller=controller, core=SimpleNamespace(config=cfg)),
        restore_after_ctx_menu=True,
        _context_menu_anchor_scroll_value=17,
        _deletion_initiated=False,
        _activate_scroll_guard=MagicMock(),
        collapsed_sections=set(),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "groups, expected",
    [
        ([], None),
        ([SimpleNamespace(group_id=3)], 3),
        ([SimpleNamespace(group_id="4"), SimpleNamespace(group_id=4)], 4),
        ([SimpleNamespace(group_id=1), SimpleNamespace(group_id=2)], None),
        ([SimpleNamespace(group_id=None)], None),
        ([SimpleNamespace(group_id=0)], None),
        ([SimpleNamespace(group_id="bad")], None),
    ],
)
def test_common_project_group_id(groups, expected):
    assert ContextList._get_common_project_group_id(groups) == expected


@pytest.mark.parametrize(
    "indexes, store, expected",
    [
        (None, "idx", set()),
        ({}, "idx", set()),
        ({"idx": {"a": {}, 2: {}}}, "idx", {"a", "2"}),
        ({"idx": ["a", 2]}, "idx", {"a", "2"}),
        ({"idx": ("a",)}, "idx", {"a"}),
        ({"idx": {"a", "b"}}, "idx", {"a", "b"}),
        ({"idx": "a"}, "idx", set()),
    ],
)
def test_ctx_store_indexes(indexes, store, expected):
    ctx = SimpleNamespace(indexes=indexes)
    assert ContextList._get_ctx_store_indexes(ctx, store) == expected


def test_load_collapsed_sections_filters_unknown_and_invalid_values():
    widget = _ctx()
    widget.window.core.config.get.return_value = ["recent", "bad", "projects", "pinned", 7]
    assert ContextList._load_collapsed_sections(widget) == {"recent", "projects", "pinned"}

    widget.window.core.config.get.return_value = "recent"
    assert ContextList._load_collapsed_sections(widget) == set()


def test_load_collapsed_sections_handles_config_failure():
    widget = _ctx()
    widget.window.core.config.get.side_effect = RuntimeError("boom")
    assert ContextList._load_collapsed_sections(widget) == set()


def test_save_collapsed_sections_persists_sorted_values():
    widget = _ctx(collapsed_sections={"recent", "pinned"})
    ContextList._save_collapsed_sections(widget)
    widget.window.core.config.set.assert_called_once_with(
        "ctx.list.sections.collapsed", ["pinned", "recent"]
    )
    widget.window.core.config.save.assert_called_once_with()


def test_selected_action_routes_open_and_new_tab():
    widget = _ctx()

    ContextList.action_open(widget, [11, 12], idx=["a"])
    widget.window.controller.ctx.load.assert_called_once_with(11, select_idx=["a"])
    assert widget.restore_after_ctx_menu is False

    widget.window.controller.ctx.load.reset_mock()
    ContextList.action_open_new_tab(widget, [11, 12])
    assert widget.window.controller.ctx.load.call_count == 2
    widget.window.controller.ctx.load.assert_any_call(11, new_tab=True)
    widget.window.controller.ctx.load.assert_any_call(12, new_tab=True)

    widget.window.controller.ctx.load.reset_mock()
    ContextList.action_open_new_tab(widget, 13, idx=5)
    widget.window.controller.ctx.load.assert_called_once_with(13, select_idx=5, new_tab=True)


def test_selected_action_routes_index_and_metadata_operations():
    widget = _ctx()
    ContextList.action_idx(widget, [1, 2], "main")
    widget.window.controller.idx.indexer.index_ctx_meta.assert_called_once_with([1, 2], "main")

    ContextList.action_idx_remove(widget, "main", ["m1", "m2"])
    widget.window.controller.idx.indexer.index_ctx_meta_remove.assert_called_once_with(
        "main", ["m1", "m2"]
    )
    assert widget.restore_after_ctx_menu is False


def test_selected_action_routes_context_mutations():
    widget = _ctx()
    ContextList.action_rename(widget, [1, 2])
    ContextList.action_pin(widget, [1, 2])
    ContextList.action_unpin(widget, 3)
    ContextList.action_important(widget, 4)
    ContextList.action_duplicate(widget, [1, 2])
    ContextList.action_copy_id(widget, [1, 2])
    ContextList.action_reset(widget, 5)
    ContextList.action_set_label(widget, [1, 2], 7)

    widget.window.controller.ctx.rename.assert_called_once_with([1, 2])
    widget.window.controller.ctx.set_important.assert_any_call([1, 2], True)
    widget.window.controller.ctx.set_important.assert_any_call(3, False)
    widget.window.controller.ctx.set_important.assert_any_call(4)
    widget.window.controller.ctx.common.duplicate.assert_called_once_with([1, 2])
    widget.window.controller.ctx.common.copy_id.assert_called_once_with([1, 2])
    widget.window.controller.ctx.common.reset.assert_called_once_with(5)
    widget.window.controller.ctx.set_label.assert_called_once_with([1, 2], 7)


def test_delete_actions_arm_scroll_guard_before_dispatch():
    widget = _ctx()
    ContextList.action_delete(widget, [1, 2])
    assert widget._deletion_initiated is True
    assert widget.restore_after_ctx_menu is False
    widget._activate_scroll_guard.assert_called_once_with("delete", 17)
    widget.window.controller.ctx.delete.assert_called_once_with([1, 2])

    widget._activate_scroll_guard.reset_mock()
    ContextList.action_group_delete_only(widget, [8, 9])
    widget._activate_scroll_guard.assert_called_once_with("group_delete_only", 17)
    widget.window.controller.ctx.delete_group.assert_called_once_with([8, 9])

    widget._activate_scroll_guard.reset_mock()
    ContextList.action_group_delete_all(widget, 8)
    widget._activate_scroll_guard.assert_called_once_with("group_delete_all", 17)
    widget.window.controller.ctx.delete_group_all.assert_called_once_with(8)


def test_group_actions_route_to_controller():
    widget = _ctx()
    ContextList.action_group_new_in_group(widget, [7, 8])
    ContextList.action_group_rename(widget, 7)
    widget.window.controller.ctx.new_in_group.assert_called_once_with(force=False, group_id=[7, 8])
    widget.window.controller.ctx.rename_group.assert_called_once_with(7)
    assert widget.restore_after_ctx_menu is False


def test_parse_drag_ids_ignores_empty_and_invalid_parts():
    mime = MagicMock()
    mime.data.return_value = b"1, 2, nope, , -3"
    widget = SimpleNamespace(_drag_mime="application/x-test")
    assert ContextList._parse_drag_ids(widget, mime) == [1, 2, -3]
    mime.data.assert_called_once_with("application/x-test")


def test_parse_drag_ids_returns_empty_on_decode_failure():
    mime = MagicMock()
    mime.data.side_effect = RuntimeError("bad mime")
    widget = SimpleNamespace(_drag_mime="application/x-test")
    assert ContextList._parse_drag_ids(widget, mime) == []


def test_delegate_status_color_returns_default_for_unknown_status():
    default = object()
    warning = object()
    delegate = SimpleNamespace(_status_colors={0: default, 1: warning})
    assert ImportantItemDelegate.get_color_for_status(delegate, 1) is warning
    assert ImportantItemDelegate.get_color_for_status(delegate, 999) is default
