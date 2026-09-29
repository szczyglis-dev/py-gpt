from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QPointF, QSizeF

from pygpt_net.ui.widget.node_editor.command import (
    AddNodeCommand,
    ClearGraphCommand,
    ConnectCommand,
    DeleteConnectionCommand,
    MoveNodeCommand,
    ResizeNodeCommand,
)


def _editor():
    editor = MagicMock()
    editor.config.cmd_add_node.return_value = "Add node"
    editor.config.cmd_move_node.return_value = "Move node"
    editor.config.cmd_resize_node.return_value = "Resize node"
    editor.config.cmd_connect.return_value = "Connect"
    editor.config.cmd_clear.return_value = "Clear"
    editor.config.cmd_delete_connection.return_value = "Delete connection"
    return editor


def test_add_node_command_creates_then_reuses_same_model_uuid():
    editor = _editor()
    node = SimpleNamespace(uuid="node-1")
    editor.graph.create_node_from_type.return_value = node
    editor._model_by_uuid.return_value = node
    pos = QPointF(10, 20)
    command = AddNodeCommand(editor, "Agent", pos)

    command.redo()
    command.redo()
    command.undo()

    editor.graph.create_node_from_type.assert_called_once_with("Agent")
    editor._prepare_new_node_defaults.assert_called_once_with(node)
    editor._add_node_model.assert_called_once_with(node, pos)
    editor._model_by_uuid.assert_called_once_with("node-1")
    editor._add_node_item.assert_called_once_with(node, pos)
    editor._remove_node_by_uuid.assert_called_once_with("node-1")


def test_move_node_command_redo_and_undo_restore_positions():
    item = MagicMock()
    item.editor.config.cmd_move_node.return_value = "Move node"
    old = QPointF(1, 2)
    new = QPointF(3, 4)
    command = MoveNodeCommand(item, old, new)

    command.redo()
    command.undo()

    assert item.setPos.call_args_list[0].args[0] == new
    assert item.setPos.call_args_list[1].args[0] == old


def test_resize_node_command_uses_clamped_resize_for_redo_and_undo():
    item = MagicMock()
    item.editor.config.cmd_resize_node.return_value = "Resize node"
    old = QSizeF(100, 50)
    new = QSizeF(200, 80)
    command = ResizeNodeCommand(item, old, new)

    command.redo()
    command.undo()

    assert item._apply_resize.call_count == 2
    assert item._apply_resize.call_args_list[0].args[0] == new
    assert item._apply_resize.call_args_list[0].kwargs == {"clamp": True}
    assert item._apply_resize.call_args_list[1].args[0] == old
    assert item._apply_resize.call_args_list[1].kwargs == {"clamp": True}


def test_connect_command_creates_connection_then_undoes_by_uuid():
    editor = _editor()
    src = SimpleNamespace(node_item=SimpleNamespace(node=SimpleNamespace(uuid="src")), prop_id="out")
    dst = SimpleNamespace(node_item=SimpleNamespace(node=SimpleNamespace(uuid="dst")), prop_id="in")
    conn = SimpleNamespace(uuid="conn-1")
    editor.graph.connect.return_value = (True, "", conn)
    command = ConnectCommand(editor, src, dst)

    command.redo()
    command.undo()

    editor.graph.connect.assert_called_once_with(("src", "out"), ("dst", "in"))
    assert command._conn_uuid == "conn-1"
    editor._remove_connection_by_uuid.assert_called_once_with("conn-1")


def test_connect_command_redo_after_undo_restores_connection_with_preserved_uuid():
    editor = _editor()
    src = SimpleNamespace(node_item=SimpleNamespace(node=SimpleNamespace(uuid="src")), prop_id="out")
    dst = SimpleNamespace(node_item=SimpleNamespace(node=SimpleNamespace(uuid="dst")), prop_id="in")
    command = ConnectCommand(editor, src, dst)
    command._conn_uuid = "conn-1"
    editor.graph.add_connection.return_value = (True, "")

    with patch("pygpt_net.ui.widget.node_editor.command.ConnectionModel") as model_cls:
        restored = model_cls.return_value
        command.redo()

    model_cls.assert_called_once_with(
        uuid="conn-1", src_node="src", src_prop="out", dst_node="dst", dst_prop="in"
    )
    editor.graph.add_connection.assert_called_once_with(restored)


def test_clear_graph_command_snapshots_only_once_and_restores_layout():
    editor = _editor()
    snapshot = {"nodes": [{"uuid": "n1"}]}
    editor.graph.to_dict.return_value = snapshot
    command = ClearGraphCommand(editor)

    command.redo()
    command.redo()
    command.undo()

    editor.graph.to_dict.assert_called_once()
    assert editor._clear_scene_and_graph.call_count == 2
    editor.load_layout.assert_called_once_with(snapshot)


def test_delete_connection_command_removes_existing_and_falls_back_to_connect_on_restore_failure():
    editor = _editor()
    editor.graph.connections = {"c1": object()}
    conn = SimpleNamespace(
        uuid="c1",
        src_node="s",
        src_prop="out",
        dst_node="d",
        dst_prop="in",
        to_dict=lambda: {
            "uuid": "c1", "src_node": "s", "src_prop": "out", "dst_node": "d", "dst_prop": "in"
        },
    )
    command = DeleteConnectionCommand(editor, conn)

    command.redo()
    editor._remove_connection_by_uuid.assert_called_once_with("c1")

    restored = SimpleNamespace(src_node="s", src_prop="out", dst_node="d", dst_prop="in")
    editor.graph.add_connection.return_value = (False, "duplicate")
    with patch("pygpt_net.ui.widget.node_editor.command.ConnectionModel.from_dict", return_value=restored):
        command.undo()

    editor.graph.add_connection.assert_called_once_with(restored)
    editor.graph.connect.assert_called_once_with(("s", "out"), ("d", "in"))
