from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.tools.agent_builder.tool import AgentBuilder
from pygpt_net.tools.audio_transcriber.tool import AudioTranscriber
from pygpt_net.tools.code_interpreter.tool import CodeInterpreter
from pygpt_net.tools.html_canvas.tool import HtmlCanvas
from pygpt_net.tools.image_viewer.tool import ImageViewer
from pygpt_net.tools.indexer.tool import IndexerTool
from pygpt_net.tools.media_player.tool import MediaPlayer
from pygpt_net.tools.text_editor.tool import TextEditor
from pygpt_net.tools.translator.tool import Translator
from pygpt_net.tools.web_browser.tool import WebBrowser


@pytest.mark.parametrize(
    "module_name, cls, action_key, callback_name",
    [
        ("pygpt_net.tools.agent_builder.tool", AgentBuilder, "agent.builder", "toggle"),
        ("pygpt_net.tools.audio_transcriber.tool", AudioTranscriber, "audio.transcribe", "toggle"),
        ("pygpt_net.tools.code_interpreter.tool", CodeInterpreter, "interpreter", "toggle"),
        ("pygpt_net.tools.html_canvas.tool", HtmlCanvas, "html_canvas", "toggle"),
        ("pygpt_net.tools.image_viewer.tool", ImageViewer, "image.viewer", "open_preview"),
        ("pygpt_net.tools.indexer.tool", IndexerTool, "indexer", "toggle"),
        ("pygpt_net.tools.media_player.tool", MediaPlayer, "media.player", "toggle"),
        ("pygpt_net.tools.text_editor.tool", TextEditor, "text.editor", "open"),
        ("pygpt_net.tools.translator.tool", Translator, "translator", "toggle"),
        ("pygpt_net.tools.web_browser.tool", WebBrowser, "web_browser", "toggle"),
    ],
)
def test_tool_setup_menu_builds_action_and_routes_trigger(module_name, cls, action_key, callback_name):
    action = MagicMock()
    callback = MagicMock()
    obj = SimpleNamespace(window=object())
    setattr(obj, callback_name, callback)

    with patch(f"{module_name}.QAction", return_value=action) as action_cls, \
            patch(f"{module_name}.QIcon", side_effect=lambda path: path), \
            patch(f"{module_name}.trans", side_effect=lambda key: f"tr:{key}"):
        actions = cls.setup_menu(obj)

    assert list(actions) == [action_key]
    assert actions[action_key] is action
    assert action_cls.call_count == 1
    action.triggered.connect.assert_called_once()

    connected = action.triggered.connect.call_args.args[0]
    connected()
    callback.assert_called_once_with()
