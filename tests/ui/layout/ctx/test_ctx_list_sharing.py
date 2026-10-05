import pytest

from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

from pygpt_net.item.ctx import CtxMeta, CtxGroup
from pygpt_net.ui.layout.ctx.ctx_list import CtxList


@pytest.fixture(autouse=True)
def translations(monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.layout.ctx.ctx_list.trans', lambda key: key)
    monkeypatch.setattr('pygpt_net.ui.layout.ctx.ctx_list.SHOW_ATTACHMENT_ICONS', True)


def test_sharing_header_keeps_conversations_visible_with_attachment_icons():
    group = CtxGroup()
    group.id, group.name = 7, "Project X"
    group.extra["attachment_share"] = True
    meta = CtxMeta()
    meta.id, meta.group_id, meta.group = 12, group.id, group
    meta.additional_ctx = [{"uuid": "plan", "name": "plans.txt", "active": True}]
    model = QStandardItemModel()
    node = SimpleNamespace(show_all_projects=True, projects_limit_collapsed_by_user=False,
                           show_all_project_contexts=set(), project_contexts_limit_collapsed_by_user=set(),
                           expanded_items=[], isExpanded=lambda index: False, setExpanded=Mock())
    ctx = SimpleNamespace(get_groups=lambda: {group.id: group}, get_search_string=lambda: "",
                          get_current_meta=lambda: meta, get_current=lambda: meta.id)
    window = SimpleNamespace(ui=SimpleNamespace(models={"ctx.list": model}, nodes={"ctx.list": node}),
                             core=SimpleNamespace(ctx=ctx, config=SimpleNamespace(get=lambda key, default=None: default),
                                                  filesystem=SimpleNamespace(get_data_dir=lambda **kwargs: "/tmp/project-X")))
    item = QStandardItem("Conversation")
    item.dt, item.isPinned = "Today", False
    widget = SimpleNamespace(window=window, _folder_icon=None, _folder_open_icon=None,
                             _group_separators=False, append_list_section=Mock(),
                             build_item=lambda *args, **kwargs: item, _set_group_icon_for_index=Mock())
    CtxList.update_groups(widget, "ctx.list", {meta.id: meta})
    assert model.rowCount() == 1
    project = model.item(0)
    assert project.rowCount() == 1 and project.child(0).text() == "Conversation"
    assert project.data(Qt.UserRole)["is_attachment"] is False
    assert "plans.txt" in project.toolTip()
    meta.additional_ctx[0]["active"] = False
    model.clear()
    widget.build_item = lambda *args, **kwargs: QStandardItem("Conversation")
    CtxList.update_groups(widget, "ctx.list", {meta.id: meta})
    assert model.item(0).data(Qt.UserRole)["is_attachment"] is False
    assert model.item(0).rowCount() == 1


def test_meta_attachment_icon_tracks_own_files_with_project_sharing():
    group = CtxGroup()
    group.extra['attachment_share'] = True
    meta = CtxMeta()
    meta.id, meta.group = 12, group
    meta.name, meta.updated = 'Conversation', 1
    context = SimpleNamespace(is_project_share_enabled=lambda meta: meta.group.extra['attachment_share'],
                              get_project_items=lambda meta: meta.group.additional_ctx + meta.additional_ctx)
    widget = SimpleNamespace(convert_date=lambda value: 'Today',
                             window=SimpleNamespace(core=SimpleNamespace(attachments=SimpleNamespace(context=context))))
    for shared in (False, True):
        group.extra['attachment_share'] = shared
        meta.additional_ctx = [{'name': 'local.txt', 'active': False}]
        item = CtxList.build_item(widget, meta.id, meta)
        assert item.data(Qt.UserRole)['is_attachment'] is True
        assert 'local.txt' in item.toolTip()
        meta.additional_ctx = []
        group.additional_ctx = [{'name': 'owned.txt', 'owner_meta_id': meta.id, 'active': False},
                                {'name': 'other.txt', 'owner_meta_id': 99}]
        item = CtxList.build_item(widget, meta.id, meta)
        assert item.data(Qt.UserRole)['is_attachment'] is True
        assert 'owned.txt' in item.toolTip()
        if not shared:
            assert 'other.txt' not in item.toolTip()
        group.additional_ctx = [{'name': 'other.txt', 'owner_meta_id': 99}]
        assert CtxList.build_item(widget, meta.id, meta).data(Qt.UserRole)['is_attachment'] is shared


def test_disabled_attachment_icons_skip_project_lookup(monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.layout.ctx.ctx_list.SHOW_ATTACHMENT_ICONS', False)
    meta = CtxMeta()
    meta.id, meta.name, meta.updated, meta.group = 12, 'Conversation', 1, CtxGroup()
    meta.additional_ctx = [{'name': 'file.txt'}]
    widget = SimpleNamespace(convert_date=lambda value: 'Today')
    item = CtxList.build_item(widget, meta.id, meta)
    assert item.data(Qt.UserRole)['is_attachment'] is False
    assert 'file.txt' not in item.toolTip()
