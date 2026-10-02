import json
from types import SimpleNamespace

import pytest

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.plugin.cmd_code_interpreter.render import Render as PythonRender
from pygpt_net.plugin.cmd_system.render import Render as SystemRender
from pygpt_net.plugin.cmd_files.render import Render as FilesRender
from tests.mocks import mock_window

from pygpt_net.core.render.web.tool_display import enrich, project


@pytest.fixture
def render_window():
    plugins = {}
    for name, renderer in [('python', PythonRender), ('system', SystemRender), ('files', FilesRender)]:
        plugin = BasePlugin()
        plugin.render = renderer(plugin)
        plugins[name] = plugin
    return SimpleNamespace(core=SimpleNamespace(plugins=SimpleNamespace(plugins=plugins)))


def test_multiple_files_preserve_names_and_literal_content(render_window):
    payload = {'cmd': 'read_file', 'result': [
        {'path': 'a.txt', 'content': '<script>no</script>\n```'},
        {'path': 'b.txt', 'content': '{"result":"literal file text"}'},
    ]}
    blocks = project(json.dumps(payload), window=render_window)
    assert [(b['label'], b['text']) for b in blocks] == [
        ('a.txt', '<script>no</script>\n```'),
        ('b.txt', '{"result":"literal file text"}'),
    ]


def test_nested_execution_keeps_both_streams_and_raw_payload(render_window):
    raw = json.dumps({'cmd': 'python_exec', 'result': {
        'result': 'combined', 'stdout': 'hello\n', 'stderr': 'warning\n'}})
    call = enrich({'name': 'python_exec', 'request': json.dumps({
        'cmd': 'python_exec', 'params': {'code': 'print("hello")'}}), 'response': raw}, window=render_window)
    assert call['response'] == raw
    assert [(b['label'], b['text']) for b in call['response_friendly']] == [
        ('STDOUT', 'hello\n'), ('STDERR', 'warning\n')]
    assert call['request_friendly'][0]['language'] == 'python'


def test_unknown_shapes_and_small_tools_fall_back_without_losing_errors(render_window):
    assert project({'cmd': 'file_info', 'result': {'size': 1}}, window=render_window) is None
    assert project({'cmd': 'read_file', 'result': [{'error': 'missing'}]}, window=render_window) is None
    assert project([{'cmd': 'tree', 'result': 'tree'}, {'cmd': 'file_info', 'result': 1}], window=render_window) is None


def test_file_writes_shell_and_tree(render_window):
    assert project({'cmd': 'append_file', 'params': {'path': 'x.txt', 'data': ''}}, direction='input', window=render_window)[0]['text'] == ''
    assert project({'cmd': 'sys_exec', 'params': {'command': 'ls'}}, direction='input', window=render_window)[0]['text'] == 'ls'
    assert project({'cmd': 'tree', 'result': '.\n└── x.txt'}, window=render_window)[0]['text'] == '.\n└── x.txt'
    assert project({'cmd': 'sys_exec', 'result': '{"foo":1}'}, window=render_window)[0]['text'] == '{"foo":1}'



def test_plugin_public_override_is_used_and_keeps_raw_unchanged():
    def display(value, name, direction):
        value['result'] = 'changed locally'
        return [{'text': 'addon text', 'label': 'STDOUT', 'language': 'text'}]

    class CustomPlugin(BasePlugin):
        def get_tool_render_rules(self):
            return {'custom_read': {
                'input': {'parser': display, 'language': 'rust'},
                'output': {'parser': display, 'language': 'python'},
            }}

    plugin = CustomPlugin()
    window = SimpleNamespace(core=SimpleNamespace(plugins=SimpleNamespace(plugins={'addon': plugin})))
    raw = {'cmd': 'custom_read', 'result': 'original'}
    assert project(raw, direction='input', window=window)[0] == {
        'text': 'addon text', 'label': 'rust', 'language': 'rust'}
    assert project(raw, window=window)[0] == {'text': 'addon text', 'label': 'STDOUT', 'language': 'python'}
    assert raw['result'] == 'original'


def test_broken_plugin_rule_falls_back_to_raw():
    def broken(*args):
        raise ValueError('bad custom parser')

    plugin = BasePlugin()
    plugin.get_tool_render_rules = lambda: {'custom': {'output': {'parser': broken}}}
    window = SimpleNamespace(core=SimpleNamespace(plugins=SimpleNamespace(plugins={'addon': plugin})))
    assert project({'cmd': 'custom', 'result': 'keep me'}, window=window) is None


def test_plugins_without_renderer_and_missing_registry_use_raw():
    plugin = BasePlugin()
    assert plugin.get_tool_render_rules() == {}
    assert project({'cmd': 'sys_exec', 'result': 'raw'}) is None


@pytest.mark.parametrize('name,params,language', [
    ('sys_exec', {'command': 'echo hi'}, 'bash'),
    ('python_exec', {'code': 'print(1)'}, 'python'),
    ('python_exec_file', {'path': 'script.py'}, 'python'),
    ('ipython_exec', {'code': 'print(1)'}, 'python'),
    ('python_sys_exec', {'command': 'ls'}, 'bash'),
    ('ipython_sys_exec', {'command': 'ls'}, 'bash'),
    ('append_file', {'path': 'a.txt', 'data': 'text'}, 'text'),
    ('save_file', {'path': 'a.txt', 'data': 'text'}, 'text'),
])
def test_input_native_language_also_labels_friendly_header(render_window, name, params, language):
    result = project({'cmd': name, 'params': params}, direction='input', window=render_window)
    assert result[0]['language'] == result[0]['label'] == language


def test_output_file_names_and_stream_labels_are_preserved(render_window):
    result = project({'cmd': 'read_file', 'result': [{'path': 'test.py', 'content': 'print(1)'}]}, window=render_window)
    assert result[0]['label'] == 'test.py'
    assert result[0]['language'] == 'text'
    streams = project({'cmd': 'python_exec', 'stdout': 'out', 'stderr': 'err', 'result': False}, window=render_window)
    assert [part['label'] for part in streams] == ['STDOUT', 'STDERR']
    assert all(part['language'] == 'text' for part in streams)


def test_builtin_plugins_statically_attach_renderer(mock_window):
    from pygpt_net.plugin.cmd_files.plugin import Plugin as FilesPlugin
    from pygpt_net.plugin.cmd_system.plugin import Plugin as SystemPlugin
    from pygpt_net.plugin.cmd_code_interpreter.plugin import Plugin as PythonPlugin

    for plugin_class, render_class in [(FilesPlugin, FilesRender), (SystemPlugin, SystemRender), (PythonPlugin, PythonRender)]:
        plugin = plugin_class(window=mock_window)
        assert isinstance(plugin.render, render_class)
        assert plugin.render.plugin is plugin
        assert plugin.get_tool_render_rules() == plugin.render.get_rules()
