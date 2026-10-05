import copy
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.plugin.filesystem import Plugin
from pygpt_net.plugin.filesystem.migration import migrate_tree
from pygpt_net.plugin.filesystem.worker import Worker, RoutedSystemWorker
from pygpt_net.plugin.filesystem.python.worker import Worker as PythonWorker
from pygpt_net.plugin.filesystem.python.execution.host import HostBackend
from pygpt_net.ui.dialog.plugins import Plugins
from pygpt_net.item.ctx import CtxItem


@pytest.mark.parametrize('ipython', [False, True])
def test_public_tools_and_section_switches(ipython):
    plugin = Plugin()
    plugin.options['use_ipython']['value'] = ipython
    data = {'cmd': []}
    plugin.cmd_syntax(data)
    names = [tool['cmd'] for tool in data['cmd']]
    assert 'python_exec' in names and 'shell_exec' in names and 'fs_read_file' in names
    assert ('python_kernel_restart' in names) == ipython
    assert not set(names).intersection({'ipython_exec', 'python_exec_file', 'python_sys_exec', 'ipython_sys_exec'})
    plugin.options['enable_python']['value'] = False
    plugin.options['enable_filesystem']['value'] = False
    data = {'cmd': []}
    plugin.cmd_syntax(data)
    assert [tool['cmd'] for tool in data['cmd']] == ['shell_exec']


def test_settings_hierarchy_and_runtime_owner():
    plugin = Plugin()
    assert list(plugin.tabs) == ['runtime', 'filesystem', 'python', 'system']
    pages = Plugins().extract_option_tabs(plugin.options)
    assert pages[:1] == ['runtime::general']
    assert [page for page in pages if page.startswith('runtime::')] == [
        'runtime::general', 'runtime::ipython', 'runtime::sandbox']
    for section in ('filesystem', 'python', 'system'):
        first = next(key for key, option in plugin.options.items() if option['tab'] == section)
        assert first == 'enable_' + section
    assert plugin.options['sandbox']['tab'] == 'runtime'
    assert 'auto_cwd' not in plugin.options


def test_migration_combines_enabled_and_config_preserves_python_runtime():
    data = {'plugins_enabled': {'cmd_files': False, 'cmd_system': True}, 'plugins': {
        'cmd_files': {'use_loaders': False, 'auto_cwd': False},
        'cmd_code_interpreter': {'sandbox': 'docker', 'use_ipython': True, 'ipython_dockerfile': 'custom',
                                 'cmd.ipython_exec': False, 'builtin_packages': 'old'},
        'cmd_system': {'sandbox': 'disabled', 'winapi_enabled': False, 'dockerfile': 'os custom'}},
        'presets': [{'config': {'cmd_files': {'use_loaders': False}}}]}
    assert migrate_tree(data, reset_runtime=True)
    assert data['plugins_enabled'] == {'filesystem': True}
    config = data['plugins']['filesystem']
    assert config['sandbox'] == 'docker'
    assert config['use_loaders'] is False
    assert config['winapi_enabled'] is False
    assert config['cmd.python_exec']['enabled'] is False
    assert config['ipython_dockerfile'] != 'custom'
    assert config['builtin_packages'] != 'old'
    assert 'filesystem' in data['presets'][0]['config']
    snapshot = copy.deepcopy(data)
    assert not migrate_tree(data, reset_runtime=True)
    assert data == snapshot


@pytest.mark.parametrize('ipython,method', [(True, 'cmd_ipython_exec'), (False, 'cmd_python_exec')])
def test_python_router_keeps_public_name(ipython, method):
    plugin = Plugin(window=MagicMock())
    plugin.options['sandbox']['value'] = 'disabled'
    plugin.options['use_ipython']['value'] = ipython
    plugin.window.controller.kernel.stopped.return_value = False
    worker = Worker()
    worker.plugin = plugin
    worker.ctx = CtxItem()
    worker.ctx.extra = {}
    worker.cmds = [{'cmd': 'python_exec', 'params': {'code': 'print(42)'}}]
    worker.reply_more = MagicMock()
    with patch.object(PythonWorker, method, return_value={'cmd': 'python_exec', 'result': '42'}) as execute:
        worker.run()
    execute.assert_called_once_with(worker.cmds[0])
    worker.reply_more.assert_called_once_with([{'cmd': 'python_exec', 'result': '42'}])


@pytest.mark.parametrize('ipython', [True, False])
def test_system_uses_selected_python_backend(ipython):
    plugin = Plugin(window=MagicMock())
    plugin.options['use_ipython']['value'] = ipython
    backend = MagicMock()
    backend.shell_exec = lambda ctx, item, request: (backend.ipython_sys_exec if ipython else backend.python_sys_exec)(ctx, item, request)
    plugin.get_execution_backend = lambda: backend
    from pygpt_net.plugin.filesystem.worker import SystemView
    worker = RoutedSystemWorker()
    worker.plugin = SystemView(plugin)
    worker.ctx = CtxItem()
    item = {'cmd': 'shell_exec', 'params': {'command': 'pwd'}}
    worker.cmd_shell_exec(item)
    selected = backend.ipython_sys_exec if ipython else backend.python_sys_exec
    selected.assert_called_once()
    other = backend.python_sys_exec if ipython else backend.ipython_sys_exec
    other.assert_not_called()


def test_host_shell_cwd(tmp_path):
    plugin = Plugin(window=MagicMock())
    plugin.window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    backend = HostBackend(plugin)
    result = backend.python_sys_exec(CtxItem(), {'params': {'command': 'pwd'}}, {})
    assert str(tmp_path) in result['stdout']
    plugin.window.core.security.ensure_command.assert_called_once_with('pwd', sandbox=False)


def test_nested_settings_render_independent_child_tabs(qt_application):
    from PySide6.QtWidgets import QVBoxLayout, QScrollArea, QTabWidget
    plugin = Plugin()
    dialog = Plugins()
    keys = dialog.extract_option_tabs(plugin.options)
    layouts = {key: QVBoxLayout() for key in keys}
    scrolls = {key: QScrollArea() for key in keys}
    widget = dialog.build_option_tab_widget(plugin, layouts, scrolls)
    assert [widget.tabText(i) for i in range(widget.count())] == list(plugin.tabs.values())
    for index in range(1, 4):
        nested = widget.widget(index)
        assert isinstance(nested, QTabWidget)
        assert nested.tabText(0) == 'General'
    runtime = widget.widget(0)
    assert [runtime.tabText(i) for i in range(runtime.count())] == [
        'General', 'Docker (IPython)', 'Docker (Python)']
    runtime.setCurrentIndex(2)
    widget.setCurrentIndex(1)
    assert widget.widget(1).currentIndex() == 0
    widget.setCurrentIndex(0)
    assert runtime.currentIndex() == 2
    widget.deleteLater()


def test_one_runtime_context_when_all_sections_disabled():
    plugin = Plugin(window=MagicMock())
    plugin.options['sandbox']['value'] = 'docker'
    plugin.window.core.filesystem.get_data_dir.return_value = '/host/project'
    plugin.window.core.filesystem.get_runtime_artifacts_dir.return_value = '/tmp/runtime_artifacts'
    plugin.window.core.config.get_user_dir.return_value = '/tmp'
    for section in plugin.command_groups:
        plugin.options['enable_' + section]['value'] = False
    ctx = CtxItem()
    prompt = plugin.on_post_prompt('System instructions.', ctx)
    assert 'Docker container' in prompt and '/host/project' in prompt and '/mnt/data' in prompt
    assert 'python_exec and shell_exec' in prompt
    assert plugin.on_post_prompt(prompt, ctx) == prompt


@pytest.mark.parametrize('windows,docker', [(False, False), (False, True), (True, False), (True, True)])
def test_skill_uses_one_active_execution_prefix(tmp_path, windows, docker):
    from pygpt_net.core.skills.skills import Skills
    window = MagicMock()
    window.core.platforms.is_windows.return_value = windows
    plugin = Plugin(window=window)
    plugin.options['sandbox']['value'] = 'docker' if docker else 'disabled'
    window.core.plugins.get.return_value = plugin
    window.controller.plugins.is_enabled.return_value = True
    window.core.filesystem.get_data_dir.return_value = str(tmp_path)
    window.core.config.get_user_dir.return_value = '/tmp/profile'
    skills = Skills(window)
    skills._display_workdir_path = lambda path, ctx=None: 'skills/example'
    context = skills._execution_context(str(tmp_path / 'skills' / 'example'))
    assert context['preferred_tool'] == 'shell_exec'
    assert context['preferred_working_directory'].endswith('/skills/example')
    assert context['shell_prefix'].startswith('cd /d' if windows and not docker else 'cd ')
    assert 'host_shell_prefix' not in context and 'sandbox_shell_prefix' not in context
    assert '/mnt/data/' in context['preferred_working_directory'] if docker else str(tmp_path) in context['preferred_working_directory']


def test_host_ipython_preserves_cell_magic_and_sets_cwd():
    from pygpt_net.plugin.filesystem.python.ipython.local_kernel import LocalKernel
    kernel = LocalKernel(MagicMock())
    kernel.init = MagicMock()
    kernel.initialized = True
    kernel.check_ready = lambda: True
    client = MagicMock()
    client.execute.side_effect = ['cwd-request', 'code-request']
    client.get_iopub_msg.return_value = {
        'parent_header': {'msg_id': 'code-request'},
        'msg_type': 'status', 'content': {'execution_state': 'idle'}}
    kernel.client = client
    kernel.execute('%%bash\npwd', current=True, cwd='/host/project')
    assert client.execute.call_args_list[0].args == ("__import__('os').chdir('/host/project')",)
    assert client.execute.call_args_list[1].args == ('%%bash\npwd',)


def test_mixed_subtab_options_share_general_page():
    dialog = Plugins()
    options = {'one': {'tab': 'example'}, 'two': {'tab': 'example', 'subtab': 'general'},
               'three': {'tab': 'example', 'subtab': 'details'}, 'four': {'tab': 'other'}}
    assert dialog.extract_option_tabs(options) == ['example::general', 'example::details', 'other']


def test_release_migration_replaces_custom_runtime_settings_once():
    from packaging.version import Version
    from pygpt_net.provider.core.config.patch import Patch
    window = MagicMock()
    data = {'__meta__': {'version': '2.9.0'}, 'plugins_enabled': {'cmd_system': True},
            'plugins': {'cmd_code_interpreter': {'sandbox': 'docker', 'ipython_dockerfile': 'CUSTOM',
                                                'builtin_packages': 'OLD'},
                        'cmd_system': {'dockerfile': 'OLD OS IMAGE'}}}
    window.core.config.all.return_value = data
    window.core.updater.post_check_config.return_value = False
    assert Patch(window).execute(Version('2.9.1'))
    config = window.core.config.data['plugins']['filesystem']
    assert config['sandbox'] == 'docker'
    assert config['ipython_dockerfile'] != 'CUSTOM'
    assert config['builtin_packages'] != 'OLD'
    assert 'OLD OS IMAGE' not in str(config)
    assert window.core.config.data['plugins_enabled'] == {'filesystem': True}
    window.core.config.data['__meta__']['version'] = '2.9.1'
    config['ipython_dockerfile'] = 'CUSTOM AFTER UPGRADE'
    window.core.config.all.return_value = window.core.config.data
    Patch(window).execute(Version('2.9.1'))
    assert config['ipython_dockerfile'] == 'CUSTOM AFTER UPGRADE'


def test_settings_without_tabs_keep_controls_visible(qt_application):
    from PySide6.QtWidgets import QVBoxLayout, QScrollArea, QLineEdit
    from pygpt_net.plugin.base.plugin import BasePlugin
    plugin = BasePlugin()
    plugin.add_option('api_key', type='text', value='example')
    dialog = Plugins()
    keys = dialog.extract_option_tabs(plugin.options)
    assert keys == ['general']
    layout = QVBoxLayout()
    control = QLineEdit('example')
    layout.addWidget(control)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    widget = dialog.build_option_tab_widget(plugin, {'general': layout}, {'general': scroll})
    widget.show()
    qt_application.processEvents()
    assert widget.tabBar().isHidden()
    assert scroll.isVisible()
    assert control.isVisible()
    assert control.text() == 'example'
    widget.close()
    widget.deleteLater()


@pytest.mark.parametrize('stored', [False, {'enabled': False, 'instruction': 'custom'}])
def test_shell_tool_settings_migration(stored):
    data = {'plugins': {'filesystem': {'cmd.sys_exec': copy.deepcopy(stored)}}}
    assert migrate_tree(data)
    assert data['plugins']['filesystem'] == {'cmd.shell_exec': stored}
    assert not migrate_tree(data)


def test_legacy_system_shell_disabled_migration():
    data = {'plugins': {'cmd_system': {'cmd.sys_exec': False}}}
    assert migrate_tree(data)
    assert data['plugins']['filesystem']['cmd.shell_exec'] is False


def test_tool_instruction_migrates_shell_name():
    data = {'prompt.cmd': 'Use sys_exec; python_sys_exec is a legacy backend name.'}
    assert migrate_tree(data)
    assert data['prompt.cmd'] == 'Use shell_exec; python_sys_exec is a legacy backend name.'
    assert not migrate_tree(data)


def test_filesystem_delivery_subtab_follows_general():
    plugin = Plugin(window=MagicMock())
    keys = Plugins().extract_option_tabs(plugin.options)
    filesystem_tabs = [key for key in keys if key.startswith('filesystem::')]
    assert filesystem_tabs[:2] == ['filesystem::general', 'filesystem::delivery']
    delivery_tools = {'fs_send_file', 'fs_deliver_file_to_user', 'fs_attach_runtime_file', 'fs_runtime_artifacts'}
    options = {key for key, option in plugin.options.items()
               if option['tab'] == 'filesystem' and option.get('subtab') == 'delivery'}
    assert options == {'cmd.' + tool for tool in delivery_tools}


@pytest.mark.parametrize('mode,available', [
    ('chat', False), ('vision', False), ('audio', False), ('research', False),
    ('agent', False), ('agent_openai', False), ('agent_v2', True), ('agent_llama', True),
])
@pytest.mark.parametrize('source', ['event', 'context'])
def test_runtime_attachment_tool_exposure_by_mode(mode, available, source):
    plugin = Plugin(window=MagicMock())
    plugin.window.core.config.get.return_value = 'agent_v2'
    ctx = CtxItem()
    ctx.mode = mode
    data = {'cmd': []}
    if source == 'event':
        data['mode'] = mode
        ctx.mode = 'agent_v2'
    plugin.cmd_syntax(data, ctx=ctx)
    names = {tool['cmd'] for tool in data['cmd']}
    assert ('fs_attach_runtime_file' in names) is available
    assert {'fs_send_file', 'fs_deliver_file_to_user', 'fs_runtime_artifacts'} <= names


def test_filesystem_tool_prefix_migration_preserves_disabled_tools():
    data = {'plugins': {'cmd_files': {'cmd.read_file': False}},
            'presets': [{'filesystem': {'cmd.append_file': {'enabled': False},
                                        'cmd.tree': True, 'cmd.fs_tree': False}}]}
    assert migrate_tree(data)
    assert data['plugins']['filesystem']['cmd.fs_read_file'] is False
    assert data['presets'][0]['filesystem'] == {
        'cmd.fs_append_file': {'enabled': False}, 'cmd.fs_tree': False}
    assert not migrate_tree(data)


def test_all_filesystem_commands_use_prefix():
    plugin = Plugin(window=MagicMock())
    assert len(plugin.command_groups['filesystem']) == 27
    assert all(name.startswith('fs_') for name in plugin.command_groups['filesystem'])


@pytest.mark.parametrize('sandbox', ['disabled', 'builtin', 'docker'])
@pytest.mark.parametrize('reply', [False, True])
def test_runtime_environment_is_prepended_to_system_prompt(sandbox, reply):
    from pygpt_net.core.events import Event
    plugin = Plugin(window=MagicMock())
    plugin.options['sandbox']['value'] = sandbox
    plugin.window.core.filesystem.get_data_dir.return_value = '/host/project'
    plugin.window.core.filesystem.get_runtime_artifacts_dir.return_value = '/tmp/runtime_artifacts'
    plugin.window.core.config.get_user_dir.return_value = '/tmp'
    ctx = CtxItem()
    ctx.reply = reply
    event = Event(Event.POST_PROMPT_END, {'value': 'Original instructions.', 'reply': reply, 'mode': 'chat'})
    event.ctx = ctx
    plugin.handle(event)
    prompt = event.data['value']
    assert prompt.startswith('EXECUTION ENVIRONMENT:')
    assert prompt.endswith('Original instructions.')
    assert 'fs_ prefix' in prompt
    assert 'python_ and shell_' in prompt
    assert '/host/project' in prompt
    if sandbox == 'docker':
        assert 'Docker working directory: /mnt/data, mapped to host working directory: /host/project' in prompt
        assert 'use Docker paths under /mnt/data' in prompt
    else:
        assert 'use host paths under /host/project' in prompt
    plugin.handle(event)
    assert event.data['value'] == prompt


@pytest.mark.parametrize('sandbox', ['disabled', 'builtin', 'docker'])
def test_runtime_context_explains_shared_temporary_directory(sandbox):
    plugin = Plugin(window=MagicMock())
    plugin.options['sandbox']['value'] = sandbox
    plugin.window.core.filesystem.get_data_dir.return_value = '/projects/work/data'
    plugin.window.core.config.get_user_dir.return_value = '/profile/tmp'
    plugin.window.core.filesystem.get_runtime_artifacts_dir.return_value = '/profile/tmp/runtime_artifacts'
    prompt = plugin.build_runtime_filesystem_context(CtxItem())
    if sandbox == 'docker':
        assert 'independent of the active project' in prompt
        assert 'Relative paths resolve against the working directory' in prompt
    if sandbox == 'docker':
        assert 'Docker temporary directory: /mnt/tmp, mapped to host temporary directory: /profile/tmp' in prompt
        assert 'execution runtime /mnt/tmp/runtime_artifacts' in prompt
    else:
        assert 'Temporary directory:' not in prompt
        assert '/mnt/tmp' not in prompt
    assert 'Use fs_runtime_artifacts' in prompt
    plugin.options['cmd.fs_runtime_artifacts']['value']['enabled'] = False
    assert 'Use fs_runtime_artifacts' not in plugin.build_runtime_filesystem_context(CtxItem())
    plugin.options['cmd.fs_runtime_artifacts']['value']['enabled'] = True
    plugin.options['enable_filesystem']['value'] = False
    assert 'Use fs_runtime_artifacts' not in plugin.build_runtime_filesystem_context(CtxItem())


@pytest.mark.parametrize('source', ['mode', 'context', 'flag'])
def test_experts_receive_agent_attachment_tool_in_chat(source):
    plugin = Plugin(window=MagicMock())
    plugin.window.core.config.get.return_value = 'chat'
    ctx = CtxItem()
    ctx.mode = 'expert' if source == 'context' else 'chat'
    data = {'cmd': [], 'mode': 'expert' if source == 'mode' else 'chat', 'is_expert': source == 'flag'}
    plugin.cmd_syntax(data, ctx)
    assert 'fs_attach_runtime_file' in {tool['cmd'] for tool in data['cmd']}
