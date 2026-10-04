"""Plugin callbacks retain their tool names and their isolated execution context."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.agents.tools import Tools
from pygpt_net.item.ctx import CtxItem


def test_native_function_tools_capture_distinct_names_and_handle_bad_specs():
    window = MagicMock()
    window.core.idx.is_valid.return_value = False
    schema = json.dumps({'type': 'object', 'properties': {'path': {'type': 'string'}}})
    window.core.command.get_functions.return_value = [
        {'name': name, 'desc': name, 'params': schema} for name in ('read', 'write', 'private')
    ] + [{'bad': True}]
    tools = Tools(window)
    tools.cmd_blacklist = ['private']
    ctx = CtxItem()
    built = tools.get_function_tools(ctx, force=True)
    assert [t.name for t in built] == ['read', 'write']
    for tool in built:
        asyncio.run(tool.on_invoke_tool(None, '{"path":"file"}'))
    assert [call.args[1] for call in window.controller.plugins.apply_cmds_all.call_args_list] == [
        [{'cmd': 'read', 'params': {'path': 'file'}}], [{'cmd': 'write', 'params': {'path': 'file'}}]]
    window.core.debug.log.assert_called_once()


def test_python_plugin_functions_and_retriever_callback():
    window = MagicMock()
    window.core.idx.is_valid.return_value = False
    window.core.command.get_functions.return_value = [{'name': 'read', 'desc': 'Read'}, {'name': 'private', 'desc': 'Private'}]
    window.controller.plugins.apply_cmds_all.return_value = 'output'
    tools = Tools(window)
    tools.cmd_blacklist = ['private']
    ctx = CtxItem()
    functions = tools.get_plugin_tools(SimpleNamespace(ctx=ctx), {}, force=True)
    assert set(functions) == {'read'}
    assert functions['read'](path='file') == 'output'
    window.controller.plugins.apply_cmds_all.assert_called_once_with(ctx, [{'cmd': 'read', 'params': {'path': 'file'}}])
    tools.tool_exec = MagicMock(return_value='retrieved')
    retriever = tools.get_openai_retriever_tool('idx')
    assert asyncio.run(retriever.on_invoke_tool(None, '{"query":"question"}')) == 'retrieved'
    assert tools.tool_exec.call_args.args[1] == {'query': 'question'}
