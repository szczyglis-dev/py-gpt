import json
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.chat.text import Text
from pygpt_net.ui.widget.textarea.annotations import ChatAnnotations
from pygpt_net.tools.web_browser.tool import WebBrowser


@pytest.fixture(autouse=True)
def translations():
    with patch('pygpt_net.ui.widget.textarea.annotations.trans', side_effect=lambda key, **kwargs: key):
        yield


def test_conversation_sessions_are_isolated_from_each_other_and_canvas():
    window = MagicMock()
    controller = Text(window)
    first = controller.get_annotations(SimpleNamespace(id=1))
    second = controller.get_annotations(SimpleNamespace(id=2))
    first.add_annotation(selection='selected answer', note='fix this')
    assert controller.get_annotations(SimpleNamespace(id=1)) is first
    assert second.get_annotations() == []
    assert WebBrowser().get_annotations() == []
    assert first.get_annotations()[0]['source'] == 'chat'
    assert 'selected answer' in first.prompt_block()
    assert 'conversation=1' in first.prompt_block()
    assert controller.get_annotations(None) is None


def test_chat_console_does_not_accept_canvas_messages_and_removes_only_own_item():
    session = ChatAnnotations(MagicMock(), 1)
    payload = json.dumps({'selection': 'answer', 'note': 'change', 'element': {}})
    with patch('PySide6.QtCore.QTimer.singleShot', side_effect=lambda delay, fn: fn()):
        assert not session.handle_annotation_console('__PYGPT_ANNOTATION_ADD__:' + payload)
        assert session.handle_annotation_console('__PYGPT_CHAT_ANNOTATION_ADD__:' + payload)
        assert len(session.annotations) == 1
        assert session.handle_annotation_console('__PYGPT_CHAT_ANNOTATION_REMOVE__:1')
        assert session.annotations == []


def test_chat_editor_scales_coordinates_and_uses_shared_editor():
    session = ChatAnnotations(MagicMock(), 1)
    view = MagicMock()
    view.zoomFactor.return_value = 2
    position = SimpleNamespace(x=lambda: 200, y=lambda: 120)
    session.show_editor(view, position, 'selected')
    script = view.page().runJavaScript.call_args.args[0]
    assert 'const px = 100, py = 60' in script
    assert '__PYGPT_CHAT_ANNOTATION_ADD__:' in script
    assert 'const preferSelection = true' in script
    assert 'stableSelector' in script
    assert WebBrowser._annotation_editor_script is ChatAnnotations._annotation_editor_script


def test_overlay_only_renders_into_views_of_own_conversation():
    session = ChatAnnotations(MagicMock(), 1)
    own, other = MagicMock(), MagicMock()
    own.meta.id, other.meta.id = 1, 2
    session.views.update([own, other])
    session.add_annotation(note='feedback')
    own.page().runJavaScript.assert_called_once()
    other.page.assert_not_called()
    assert '__PYGPT_CHAT_ANNOTATION_REMOVE__:' in own.page().runJavaScript.call_args.args[0]
