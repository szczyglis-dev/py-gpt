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


def test_file_annotations_are_scoped_in_prompt_and_excluded_from_chat_overlay():
    session = ChatAnnotations(MagicMock(), 7)
    session.add_annotation(selection='chat text', note='chat note')
    item = session.add_file_annotation('src/example.py', 2, 4, 'file text', 'file note')
    prompt = session.prompt_block()
    assert 'FILES PREVIEW USER ANNOTATIONS (source=files; conversation=7)' in prompt
    assert 'src/example.py' in prompt
    assert 'chat note' in prompt
    assert 'file note' not in session._annotation_overlay_script()
    assert ChatAnnotations(MagicMock(), 8).prompt_block() == ''
    session._remove_annotation(item['id'])
    assert 'file note' not in session.prompt_block()
    assert 'chat note' in session.prompt_block()


@pytest.mark.parametrize('source,key', [
    ('canvas_web', 'ctx.annotations.clear_on_send.canvas'),
    ('chat', 'ctx.annotations.clear_on_send.chat'),
    ('files', 'ctx.annotations.clear_on_send.files'),
])
@pytest.mark.parametrize('enabled', [True, False])
def test_clear_only_delivered_annotations_and_refresh_popups(source, key, enabled):
    from pygpt_net.ui.widget.textarea import annotations as module
    window = MagicMock()
    window.core.config.get.side_effect = lambda config_key, default=False: enabled if config_key == key else default
    session = ChatAnnotations(window, 1)
    session._render_annotations = MagicMock()
    session.annotations = [dict(id=1, source=source, note='sent')]
    ctx = SimpleNamespace()
    module.track_sent_annotations(ctx, session, session.annotations)
    assert len(session.annotations) == 1  # preparing a request never consumes it
    session.annotations.append(dict(id=2, source=source, note='added while sending'))
    module.clear_sent_annotations(ctx)
    assert [item['id'] for item in session.annotations] == ([2] if enabled else [1, 2])
    assert session._render_annotations.call_count == int(enabled)
    module.clear_sent_annotations(ctx)
    assert session._render_annotations.call_count == int(enabled)


def test_prompt_tracks_only_included_annotations_and_keeps_other_conversations():
    from pygpt_net.ui.widget.textarea.annotations import clear_sent_annotations
    session = ChatAnnotations(MagicMock(), 1)
    other = ChatAnnotations(MagicMock(), 2)
    for index in range(25):
        session.add_file_annotation('file.py', index + 1, index + 1, 'text', str(index))
    other.add_file_annotation('other.py', 1, 1, 'text', 'keep')
    ctx = SimpleNamespace()
    prompt = session.prompt_block(ctx)
    assert len(session.annotations) == 25
    assert '"note": "24"' in prompt
    clear_sent_annotations(ctx)
    assert [item['note'] for item in session.annotations] == [str(i) for i in range(5)]
    assert len(other.annotations) == 1


def test_canvas_prompt_is_preserved_until_delivery_and_reset_ids_are_safe():
    from pygpt_net.item.ctx import CtxItem
    from pygpt_net.plugin.canvas_web.plugin import Plugin
    from pygpt_net.ui.widget.textarea.annotations import clear_sent_annotations
    window = MagicMock()
    browser = WebBrowser()
    browser.annotations = [dict(id=1, time=1, source='canvas_web', note='sent note')]
    browser._render_annotations = MagicMock()
    window.tools.get.return_value = browser
    ctx = CtxItem()
    prompt = Plugin.append_runtime_context(SimpleNamespace(window=window), 'system', ctx)
    assert 'sent note' in prompt
    assert len(browser.annotations) == 1
    # A runtime/profile reset may reuse the sequence number while a response is pending.
    browser.annotations = [dict(id=1, time=2, source='canvas_web', note='new runtime')]
    clear_sent_annotations(ctx)
    assert browser.annotations[0]['note'] == 'new runtime'
    browser._render_annotations.assert_not_called()
    assert '_sent_annotation_batches' not in ctx.to_dict()


def test_annotation_prompt_directs_feedback_to_its_source():
    session = ChatAnnotations(MagicMock(), 1)
    session.add_annotation(selection='answer', note='fix wording')
    session.add_file_annotation('src/app.py', 2, 3, 'code', 'fix code')
    prompt = session.prompt_block()
    assert 'Apply the feedback to your answer in chat' in prompt
    assert 'Apply the feedback to those files using file tools when changes are requested' in prompt
    assert 'Do not call canvas_set_html or other canvas tools merely to handle them' in prompt
    assert 'fix wording' in prompt and 'fix code' in prompt
