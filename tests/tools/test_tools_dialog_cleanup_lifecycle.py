from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.agent_builder.ui.dialogs import BuilderDialog
from pygpt_net.tools.audio_transcriber.ui.dialogs import AudioTranscribeDialog
from pygpt_net.tools.code_interpreter.ui.dialogs import ToolDialog as InterpreterDialog
from pygpt_net.tools.html_canvas.ui.dialogs import ToolDialog as CanvasDialog
from pygpt_net.tools.indexer.ui.dialogs import IndexerDialog
from pygpt_net.tools.media_player.ui.dialogs import VideoPlayerDialog
from pygpt_net.tools.translator.ui.dialogs import ToolDialog as TranslatorDialog
from pygpt_net.tools.web_browser.ui.dialogs import ToolDialog as BrowserDialog


def _window_with_tool(tool_id, tool):
    tools = MagicMock()
    tools.get.return_value = tool
    return SimpleNamespace(tools=tools)


def test_audio_transcriber_dialog_cleanup_notifies_tool():
    tool = MagicMock()
    obj = SimpleNamespace(window=_window_with_tool("transcriber", tool))

    AudioTranscribeDialog.cleanup(obj)

    obj.window.tools.get.assert_called_once_with("transcriber")
    tool.on_close.assert_called_once_with()


def test_indexer_dialog_cleanup_notifies_tool():
    tool = MagicMock()
    obj = SimpleNamespace(window=_window_with_tool("indexer", tool))

    IndexerDialog.cleanup(obj)

    obj.window.tools.get.assert_called_once_with("indexer")
    tool.on_close.assert_called_once_with()


def test_media_player_dialog_cleanup_notifies_tool():
    tool = MagicMock()
    obj = SimpleNamespace(window=_window_with_tool("player", tool))

    VideoPlayerDialog.cleanup(obj)

    obj.window.tools.get.assert_called_once_with("player")
    tool.on_close.assert_called_once_with()


def test_interpreter_dialog_cleanup_closes_and_updates_tool():
    tool = MagicMock()
    window = _window_with_tool("interpreter", tool)
    obj = SimpleNamespace(window=window)

    InterpreterDialog.cleanup(obj)

    assert tool.opened is False
    tool.close.assert_called_once_with()
    tool.update.assert_called_once_with()
    assert window.tools.get.call_count == 3


def test_interpreter_dialog_cleanup_ignores_missing_window():
    assert InterpreterDialog.cleanup(SimpleNamespace(window=None)) is None


def _assert_generic_tool_dialog_cleanup(dialog_cls):
    tool = MagicMock()
    tool.opened = True
    obj = SimpleNamespace(window=object(), tool=tool)

    dialog_cls.cleanup(obj)

    assert tool.opened is False
    tool.close.assert_called_once_with()
    tool.update.assert_called_once_with()

    tool.reset_mock()
    assert dialog_cls.cleanup(SimpleNamespace(window=None, tool=tool)) is None
    assert dialog_cls.cleanup(SimpleNamespace(window=object(), tool=None)) is None
    tool.close.assert_not_called()


def test_canvas_dialog_cleanup_closes_and_updates_tool():
    _assert_generic_tool_dialog_cleanup(CanvasDialog)


def test_translator_dialog_cleanup_closes_and_updates_tool():
    _assert_generic_tool_dialog_cleanup(TranslatorDialog)


def test_browser_dialog_cleanup_closes_and_updates_tool():
    _assert_generic_tool_dialog_cleanup(BrowserDialog)


def test_agent_builder_cleanup_is_idempotent_and_drops_ui_references():
    tool = MagicMock()
    agents_list = MagicMock()
    editor = MagicMock()
    legend = MagicMock()
    help_label = MagicMock()
    ui = SimpleNamespace(
        nodes={
            "agent.builder.list": agents_list,
            "agent.builder.splitter": None,
            "agent.builder.legend": legend,
            "agent.builder.list.help": help_label,
        },
        editor={"agent.builder": editor},
    )
    tools = MagicMock()
    tools.get.return_value = tool
    obj = SimpleNamespace(_cleaned=False, window=SimpleNamespace(tools=tools, ui=ui))

    with patch("PySide6.QtWidgets.QApplication.sendPostedEvents"), \
            patch("PySide6.QtWidgets.QApplication.processEvents"):
        BuilderDialog.cleanup(obj)
        BuilderDialog.cleanup(obj)

    assert obj._cleaned is True
    tools.get.assert_called_once_with("agent_builder")
    tool.on_close.assert_called_once_with()
    agents_list.cleanup.assert_called_once_with()
    assert "agent.builder" not in ui.editor
    editor.setStyleSheet.assert_called_once_with("")
    editor.close.assert_called_once_with()
    editor.setParent.assert_called_once_with(None)
    editor.deleteLater.assert_called_once_with()
    legend.setParent.assert_called_once_with(None)
    legend.deleteLater.assert_called_once_with()
    help_label.setParent.assert_called_once_with(None)
    help_label.deleteLater.assert_called_once_with()
    assert "agent.builder.legend" not in ui.nodes
    assert "agent.builder.list.help" not in ui.nodes
    assert "agent.builder.splitter" not in ui.nodes
