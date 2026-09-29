from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.events import Event
from pygpt_net.plugin.canvas_web.plugin import Plugin


@pytest.fixture
def plugin(monkeypatch):
    monkeypatch.setattr(Plugin, 'init_options', lambda self: None)
    plugin = Plugin()
    plugin.window = MagicMock()
    plugin.window.core.ctx.get_current_meta.return_value = SimpleNamespace(id=1)
    plugin.window.controller.chat.text.annotations = {}
    plugin.has_cmd = lambda name: True
    plugin.get_cmd = lambda name: {'name': name}
    return plugin


def tools(plugin, event_type=Event.CMD_SYNTAX, ctx=None):
    event = Event(event_type, {'cmd': []}, ctx=ctx)
    plugin.handle(event)
    return {item['name'] for item in event.data['cmd']}


@pytest.mark.parametrize('event_type', [Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE])
@pytest.mark.parametrize('source', ['chat', 'files'])
def test_hides_canvas_retrieval_until_conversation_annotations_are_removed(plugin, event_type, source):
    session = SimpleNamespace(annotations=[{'source': source}])
    plugin.window.controller.chat.text.annotations[1] = session
    assert tools(plugin, event_type) == set(plugin.allowed_cmds) - {'canvas_annotations'}
    session.annotations.clear()
    assert tools(plugin, event_type) == set(plugin.allowed_cmds)


def test_annotations_in_other_conversation_do_not_hide_tool(plugin):
    plugin.window.controller.chat.text.annotations[2] = SimpleNamespace(annotations=[{'source': 'files'}])
    assert 'canvas_annotations' in tools(plugin)
    assert 'canvas_annotations' not in tools(plugin, ctx=SimpleNamespace(meta=SimpleNamespace(id=2)))


def test_canvas_annotations_and_missing_conversation_keep_tool_available(plugin):
    plugin.window.controller.chat.text.annotations[1] = SimpleNamespace(annotations=[{'source': 'canvas_web'}])
    assert 'canvas_annotations' in tools(plugin)
    plugin.window.core.ctx.get_current_meta.return_value = None
    assert 'canvas_annotations' in tools(plugin)


def test_canvas_system_prompt_scopes_chat_and_file_feedback(plugin):
    prompt = plugin.on_system_prompt('original instructions')
    assert prompt.startswith('original instructions')
    assert 'Keep ordinary answers and revisions to chat answers in chat' in prompt
    assert 'source=chat refer to conversation text' in prompt
    assert 'source=files refer to the specified file and line range' in prompt
    assert 'do not create or update a canvas merely because an annotation is present' in prompt
