from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from pygpt_net.tools.files import Files
from pygpt_net.tools.base import BaseTool


def make_tool(root):
    window = MagicMock()
    window.core.filesystem.get_data_dir.return_value = str(root)
    window.core.config.get.side_effect = lambda key, default=None: default
    window.controller.tabs.get_tabs_by_tool.return_value = []
    tool = Files()
    tool.attach(window)
    return tool, window


def test_services_work_without_frontend_and_reload_does_not_open_tab(tmp_path):
    tool, window = make_tool(tmp_path)
    assert isinstance(tool, BaseTool)
    assert tool.allow_tab and not tool.multi_tab
    tool.chat.uploaded_ids.append('old')
    tool.on_reload()
    assert tool.chat.uploaded_ids == []
    assert tool.explorer is None
    window.controller.tabs.open_or_activate.assert_not_called()
    tool.chat.attach(str(tmp_path / 'attachment.txt'))
    window.core.attachments.new.assert_called_once_with(
        mode=None, name='attachment.txt', path=str(tmp_path / 'attachment.txt'), auto_save=False)
    window.core.attachments.save.assert_called_once()


def test_real_frontend_refresh_focus_cleanup_and_reopen(qapp, tmp_path):
    root = tmp_path / 'first'
    root.mkdir()
    source = root / 'test.txt'
    source.write_text('before')
    tool, window = make_tool(root)
    tab = SimpleNamespace(column_idx=1)
    explorer = tool.as_tab(tab)
    assert explorer.preview.open_file(str(source))
    explorer.preview.viewer.setPlainText('after')
    assert explorer.preview.save()
    assert source.read_text() == 'after'
    explorer.eventFilter(explorer.treeView.viewport(), QEvent(QEvent.MouseButtonPress))
    window.controller.tabs.on_column_focus.assert_called_with(1)
    second = tmp_path / 'second'
    second.mkdir()
    window.core.filesystem.get_data_dir.return_value = str(second)
    tool.refresh(reload=True)
    assert explorer.directory == explorer.preview.root == str(second)
    assert explorer.model.rootPath() == str(second)
    explorer.on_delete()
    assert tool.explorer is None
    assert not tool._surfaces
    assert explorer.tree_search.cancelled.is_set()
    assert not explorer.tree_search.timer.isActive()
    tool.refresh(reload=True)
    window.controller.tabs.open_or_activate.assert_not_called()
    new = tool.as_tab(tab)
    assert new is not explorer
    assert new.directory == str(second)
    new.on_delete()
    explorer.deleteLater()
    new.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.mark.parametrize('modifier', [Qt.ControlModifier, Qt.ShiftModifier,
                                    Qt.ControlModifier | Qt.ShiftModifier])
@pytest.mark.parametrize('expanded', [False, True])
def test_modified_folder_click_keeps_expansion(qapp, tmp_path, monkeypatch, modifier, expanded):
    from PySide6.QtGui import QGuiApplication
    folder = tmp_path / 'folder'
    folder.mkdir()
    tool, window = make_tool(tmp_path)
    explorer = tool.as_tab(SimpleNamespace(column_idx=0))
    index = explorer.model.index(str(folder))
    explorer.treeView.setExpanded(index, expanded)
    monkeypatch.setattr(QGuiApplication, 'keyboardModifiers', lambda: modifier)
    explorer.on_tree_clicked(index)
    assert explorer.treeView.isExpanded(index) == expanded
    monkeypatch.setattr(QGuiApplication, 'keyboardModifiers', lambda: Qt.NoModifier)
    explorer.on_tree_clicked(index)
    assert explorer.treeView.isExpanded(index) != expanded
    explorer.on_delete()
    explorer.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
