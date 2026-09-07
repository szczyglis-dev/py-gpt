from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.layout.chat.attachments import Attachments


def _attachments():
    model = MagicMock()
    window = SimpleNamespace(
        ui=SimpleNamespace(models={"attachments": model}, nodes={}),
        core=SimpleNamespace(filesystem=SimpleNamespace(sizeof_fmt=MagicMock(side_effect=lambda size: f"{size} B")), debug=MagicMock()),
        controller=SimpleNamespace(attachment=MagicMock()),
    )
    return SimpleNamespace(window=window, id="attachments", _dnd_handlers={}), model


def test_centered_checkbox_helpers_use_expected_nodes():
    widget, _ = _attachments()
    widget.window.ui.nodes.update({
        "attachments.send_clear": "send",
        "attachments.capture_clear": "capture",
        "attachments.auto_index": "index",
    })
    widget._centered_container = MagicMock(side_effect=lambda child: f"box:{child}")
    assert Attachments.setup_send_clear(widget) == "box:send"
    assert Attachments.setup_capture_clear(widget) == "box:capture"
    assert Attachments.setup_auto_index(widget) == "box:index"


def test_update_populates_name_path_size_and_context(tmp_path):
    widget, model = _attachments()
    file_path = tmp_path / "file.bin"
    file_path.write_bytes(b"abcd")
    file_item = SimpleNamespace(type="file", path=str(file_path), name="file.bin", ctx=True)
    url_item = SimpleNamespace(type="url", path="https://example.com", name="web", ctx=False)
    data = OrderedDict([("f", file_item), ("u", url_item)])

    with patch("pygpt_net.ui.layout.chat.attachments.AttachmentItem.TYPE_FILE", "file"):
        Attachments.update(widget, data)

    model.setRowCount.assert_called_once_with(2)
    model.beginResetModel.assert_called_once_with()
    model.endResetModel.assert_called_once_with()
    values = [call.args[1] for call in model.setData.call_args_list]
    assert values == ["file.bin", str(file_path), "4 B", "YES", "web", "https://example.com", "", ""]
    model.dataChanged.emit.assert_called_once()


def test_update_empty_data_does_not_emit_data_changed():
    widget, model = _attachments()
    Attachments.update(widget, {})
    model.setRowCount.assert_called_once_with(0)
    model.dataChanged.emit.assert_not_called()


def test_setup_attachments_registers_drop_handler():
    widget, _ = _attachments()
    node = MagicMock()
    model = MagicMock()
    widget.window.ui.nodes["attachments"] = node
    widget.create_model = MagicMock(return_value=model)
    handler = object()
    with patch("pygpt_net.ui.layout.chat.attachments.AttachmentList", return_value=node), \
         patch("pygpt_net.ui.layout.chat.attachments.AttachmentDropHandler", return_value=handler):
        Attachments.setup_attachments(widget)
    node.setModel.assert_called_once_with(model)
    assert widget._dnd_handlers["attachments"] is handler


def test_setup_attachments_logs_drop_handler_error():
    widget, _ = _attachments()
    node = MagicMock()
    widget.create_model = MagicMock(return_value=MagicMock())
    with patch("pygpt_net.ui.layout.chat.attachments.AttachmentList", return_value=node), \
         patch("pygpt_net.ui.layout.chat.attachments.AttachmentDropHandler", side_effect=RuntimeError("dnd")):
        Attachments.setup_attachments(widget)
    widget.window.core.debug.log.assert_called_once()
