from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QWidget

from pygpt_net.tools.files.ui.menus import Menus


@pytest.mark.parametrize('multiple', [False, True])
def test_context_menu_index_actions_connect_and_forward_loader(qapp, tmp_path, monkeypatch, multiple):
    paths = [str(tmp_path / 'one.txt')]
    if multiple:
        paths.append(str(tmp_path / 'two.txt'))
    for path in paths:
        Path(path).write_text('content')
    explorer = QWidget()
    explorer.window = window = MagicMock()
    explorer.tool = MagicMock()
    explorer.clipboard = MagicMock()
    explorer.archives = MagicMock()
    explorer.selected_paths = lambda: paths
    explorer.parent_for_selection = lambda selected: str(tmp_path)
    explorer.model = SimpleNamespace(get_index_status=lambda path: {
        'indexed': True, 'global_indexes': ['old'], 'project_indexes': []})
    names = ('open', 'open_dir', 'download', 'rename', 'duplicate', 'touch', 'mkdir',
             'refresh', 'upload', 'delete', 'copy', 'cut', 'paste', 'read', 'attachment', 'db', 'pack')
    explorer._icons = {name: QIcon() for name in names}
    window.core.filesystem.actions.has_preview.return_value = False
    window.core.filesystem.actions.has_use.return_value = False
    window.core.filesystem.packer.can_unpack.return_value = False
    window.core.config.get.return_value = [
        {'id': 'first', 'name': 'First'}, {'id': 'second', 'name': 'Second'}]
    window.core.idx.project.get_current_group_id.return_value = None
    window.core.idx.project.is_virtual.return_value = False
    window.core.idx.resolve_idx.side_effect = lambda index: index
    captured = []
    class NonBlockingMenu(QMenu):
        def exec(self, *args):
            captured.append(self)

    monkeypatch.setattr('pygpt_net.tools.files.ui.menus.QMenu', NonBlockingMenu)
    Menus(explorer).context(None)
    index_menu = next(action.menu() for action in captured[0].actions()
                      if action.menu() and any(a.text().startswith('IDX:') for a in action.menu().actions()))
    for action in index_menu.actions():
        if not action.isSeparator():
            action.trigger()
    target = paths if multiple else paths[0]
    indexer = window.controller.idx.indexer
    assert indexer.index_file.call_args_list == [
        call(target, 'first', show_loader=True), call(target, 'second', show_loader=True)]
    indexer.index_file_remove.assert_called_once_with(target, 'old', show_loader=True)
    explorer.deleteLater()
