import shutil
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtWidgets import QTreeView, QWidget

from pygpt_net.tools.files.core.clipboard import Clipboard
from pygpt_net.tools.files.ui.drop import ExplorerDropHandler


@pytest.mark.parametrize('mode', ['move', 'import', 'fallback'])
def test_drop_uses_components_and_reveals_result(qapp, tmp_path, mode):
    source = tmp_path / 'item.txt'
    source.write_text('payload')
    target = tmp_path / 'target'
    target.mkdir()
    explorer = QWidget()
    explorer.treeView = QTreeView(explorer)
    explorer.window = SimpleNamespace(core=SimpleNamespace(debug=MagicMock()))
    importer = MagicMock()
    if mode == 'fallback':
        importer.side_effect = RuntimeError('import unavailable')
    else:
        importer.side_effect = lambda paths, destination: shutil.copy2(paths[0], destination)
    explorer.tool = SimpleNamespace(transfers=SimpleNamespace(import_paths=importer))
    explorer.clipboard = Clipboard(explorer)
    explorer.expand_directory = MagicMock()
    explorer.reveal = MagicMock()
    handler = ExplorerDropHandler(explorer)
    handler._calc_context = lambda pos: None
    handler._target_dir_from_context = lambda ctx: str(target)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = SimpleNamespace(
        type=lambda: QEvent.Drop, mimeData=lambda: mime,
        source=lambda: explorer.treeView if mode == 'move' else None,
        position=lambda: QPointF(QPoint(0, 0)),
        setDropAction=MagicMock(), acceptProposedAction=MagicMock(), accept=MagicMock())
    assert handler.eventFilter(explorer.treeView.viewport(), event)
    destination = target / source.name
    assert destination.read_text() == 'payload'
    assert source.exists() == (mode != 'move')
    explorer.expand_directory.assert_called_once_with(str(target), center=False)
    explorer.reveal.assert_called_once_with([str(destination)], select_first=True)
    explorer.window.core.debug.log.assert_not_called()
    event.setDropAction.assert_called_once_with(Qt.MoveAction if mode == 'move' else Qt.CopyAction)
    event.acceptProposedAction.assert_called_once_with()
    if mode == 'move':
        importer.assert_not_called()
    else:
        importer.assert_called_once_with([str(source)], str(target))
    explorer.deleteLater()
