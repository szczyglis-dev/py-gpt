"""Integrated host filesystem, Python and system tools."""
import copy
import platform
from pygpt_net.core.events import Event
from .python.runtime import PythonRuntime
from .filesystem.helpers import FilesystemHelpers
from .os.runner import Runner as SystemRunner
from .config import Config
from .render import Render
from .filesystem.output import Output as FilesOutput


class Plugin(PythonRuntime):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = 'filesystem'
        self.name = 'Filesystem, Python and OS'
        self.description = 'Host filesystem tools, Python execution and system commands with one shared runtime.'
        self.type = ['interpreter', 'os']
        self.use_locale = False
        self.system_runner = SystemRunner(self)
        self.render = Render(self)
        self.file_output = FilesOutput(self)
        self.command_groups = {
            'filesystem': [key[4:] for key, option in self.options.items()
                           if key.startswith('cmd.') and option['tab'] == 'filesystem'],
            'python': ['python_exec', 'python_kernel_restart'],
            'system': [key[4:] for key, option in self.options.items()
                       if key.startswith('cmd.') and option['tab'] == 'system'],
        }
        self.allowed_cmds = [cmd for group in self.command_groups.values() for cmd in group]

    def init_options(self):
        self.config = Config(self)
        self.config.from_defaults(self)

    def is_command_active(self, cmd):
        for section, commands in self.command_groups.items():
            if cmd in commands:
                if not self.get_option_value('enable_' + section):
                    return False
                if cmd == 'python_kernel_restart':
                    return self.is_ipython_enabled()
                if cmd.startswith('win_'):
                    return platform.system() == 'Windows' and bool(self.get_option_value('winapi_enabled'))
                return True
        return False

    def has_cmd(self, cmd):
        return self.is_command_active(cmd) and super().has_cmd(cmd)

    def cmd_syntax(self, data, ctx=None):
        mode = data.get('mode') or getattr(ctx, 'mode', None)
        for cmd in self.allowed_cmds:
            if cmd == 'fs_attach_runtime_file' and not self.is_runtime_attach_mode(mode, ctx=ctx, is_expert=data.get('is_expert', False)):
                continue
            if not self.has_cmd(cmd):
                continue
            syntax = copy.deepcopy(self.get_cmd(cmd))
            if cmd == 'python_exec':
                syntax['instruction'] += (' Uses a persistent IPython kernel.' if self.is_ipython_enabled()
                                          else ' Uses the standard Python interpreter in a new process per call.')
            data['cmd'].append(syntax)

    def handle(self, event, *args, **kwargs):
        if event.name == Event.POST_PROMPT_END:
            event.data['value'] = self.on_post_prompt(event.data['value'], event.ctx, event.data.get('mode'))
        elif event.name == Event.TOOL_OUTPUT_RENDER and event.data.get('tool') == self.id:
            content = event.data.get('content')
            if isinstance(content, dict) and content.get('cmd') in self.command_groups['filesystem']:
                event.data['html'] = self.file_output.handle(event.ctx, content)
            else:
                event.data['html'] = ''
        elif event.name == Event.MODELS_CHANGED:
            self.refresh_option('model_tmp_query')
        else:
            super().handle(event, *args, **kwargs)

    def build_runtime_filesystem_context(self, ctx=None):
        host = self.window.core.filesystem.get_data_dir(ctx=ctx)
        runtime = self.get_runtime_workdir(ctx=ctx)
        environment = 'Docker container' if self.is_docker_sandbox() else (
            'Built-in Python environment on the host' if self.is_builtin_sandbox() else 'host')
        host_tmp = self.window.core.config.get_user_dir('tmp')
        runtime_tmp = self.map_host_path_to_runtime(host_tmp, ctx=ctx)
        artifacts = self.window.core.filesystem.get_runtime_artifacts_dir(create=False)
        visible_artifacts = self.map_host_path_to_runtime(artifacts, ctx=ctx)
        permissions = ''
        if self.is_docker_sandbox():
            root = self.get_option_value('ipython_run_as_root' if self.is_ipython_enabled() else 'docker_run_as_root')
            permissions = ('The Docker runtime runs as root; sudo is not required. ' if root else
                           "The Docker runtime runs as the pygpt user; passwordless sudo is available. ")
        if self.is_docker_sandbox():
            paths = (f'Docker working directory: {runtime}, mapped to host working directory: {host}.\n'
                     f'Filesystem tools with the fs_ prefix use host paths under {host}.\n'
                     f'Execution tools with the python_ and shell_ prefixes use Docker paths under {runtime}.\n')
        else:
            paths = (f'Working directory: {host}.\n'
                     f'Filesystem tools with the fs_ prefix and execution tools with the python_ and shell_ '
                     f'prefixes use host paths under {host}.\n')
        temporary = ''
        artifact_paths = ''
        if self.is_docker_sandbox():
            temporary = (
                f'Docker temporary directory: {runtime_tmp}, mapped to host temporary directory: {host_tmp}. '
                f'Use host paths under {host_tmp} with fs_ tools and Docker paths under {runtime_tmp} '
                'with python_ and shell_ tools.\n'
                'This shared temporary directory belongs to the application profile and is independent of '
                'the active project. Relative paths resolve against the working directory.\n'
            )
            artifact_paths = f'Runtime artifacts: host {artifacts}; execution runtime {visible_artifacts}. '
        artifact_tool = ('Use fs_runtime_artifacts to resolve files from previous tool results. '
                         if self.has_cmd('fs_runtime_artifacts') else '')
        os_name = 'Linux' if self.is_docker_sandbox() else platform.system()
        return (f'EXECUTION ENVIRONMENT: {environment}. Operating system: {os_name}. {permissions}\n' +
                paths + temporary +
                f'python_exec and shell_exec share the runtime working directory: {runtime}.\n' +
                artifact_paths +
                artifact_tool +
                'Use host_path with filesystem tools (fs_ prefix) and runtime_paths.filesystem with execution tools '
                '(python_ and shell_ prefixes). '
                'These paths are internal; expose them only when the user requests a path.')

    def on_post_prompt(self, prompt, ctx, mode=None):
        if ctx is not None and isinstance(ctx.extra, dict):
            ctx.extra.pop("agents_v2_filesystem_context", None)
        context = self.build_runtime_filesystem_context(ctx=ctx)
        return prompt if context in prompt else context + "\n\n" + prompt

    is_runtime_attach_mode = FilesystemHelpers.is_runtime_attach_mode
    get_index_names = FilesystemHelpers.get_index_names
    get_index_name = FilesystemHelpers.get_index_name
    read_as_text = FilesystemHelpers.read_as_text
    get_code_interpreter_sandbox_modes = FilesystemHelpers.get_code_interpreter_sandbox_modes
    is_ipython_sandbox_active = FilesystemHelpers.is_ipython_sandbox_active
    is_legacy_sandbox_active = FilesystemHelpers.is_legacy_sandbox_active

    def handle_python_run(self, code):
        # The interpreter UI uses the same public command as model calls.
        use_ipython = self.is_ipython_enabled()
        from pygpt_net.item.ctx import CtxItem
        if use_ipython and self.get_option_value('fresh_kernel'):
            backend = self.get_execution_backend()
            runtime = getattr(backend, 'runtime', None)
            if runtime is None or runtime.is_ready():
                backend.restart_ipython()
        ctx = CtxItem()
        self.cmd(ctx, [{'cmd': 'python_exec', 'params': {'code': code}, 'silent': True, 'force': True}], True)
        self.window.tools.get('interpreter').auto_open()
