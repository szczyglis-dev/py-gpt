"""Settings assembled from the three tool providers and one shared runtime."""
from pygpt_net.plugin.base.config import BaseConfig
from pygpt_net.plugin.base.plugin import BasePlugin
from .python.config import Config as PythonConfig
from .filesystem.config import Config as FilesConfig
from .os.config import Config as SystemConfig
from pygpt_net.core.sandbox.native_tools import NativeTools


class Config(BaseConfig):
    def from_defaults(self, plugin=None):
        plugin = plugin or self.plugin
        plugin.tabs = {'runtime': 'Runtime / sandbox', 'filesystem': 'Filesystem',
                       'python': 'Python', 'system': 'System (OS)'}
        plugin.subtabs = {'ipython': 'Docker (IPython)', 'sandbox': 'Docker (Python)'}
        for section, config, domain in (
                ('filesystem', FilesConfig, 'plugin.filesystem'),
                ('python', PythonConfig, 'plugin.filesystem'),
                ('system', SystemConfig, 'plugin.filesystem')):
            provider = BasePlugin()
            config(provider).from_defaults(provider)
            plugin.add_option('enable_' + section, type='bool', value=True,
                              label={'filesystem': 'Enable filesystem', 'python': 'Enable Python interpreter',
                                     'system': 'Enable System (OS)'}[section],
                              description='Enables support for and access to the tools in this section.',
                              _locale_domain=domain, _use_locale=True,
                              tab=section, subtab='general')
            for key, option in provider.options.items():
                option = dict(option)
                old_tab = option.get('tab') or 'general'
                if section == 'filesystem' and key == 'auto_cwd':
                    continue
                if section == 'system' and (old_tab in ('sandbox', 'builtin_sandbox') or
                                            key in ('sandbox', 'auto_cwd', 'attach_output')):
                    continue
                if section == 'python' and key in (
                        'cmd.ipython_exec', 'cmd.ipython_sys_exec', 'cmd.python_sys_exec',
                        'cmd.python_exec_file', 'cmd.ipython_kernel_restart'):
                    continue
                if section == 'python' and (old_tab in ('ipython', 'sandbox', 'python_legacy', 'builtin_sandbox')
                                            or key == 'sandbox') and key != 'python_cmd_tpl':
                    option['tab'] = 'runtime'
                    option['subtab'] = 'sandbox' if old_tab == 'python_legacy' else (old_tab if old_tab in ('ipython', 'sandbox', 'builtin_sandbox') else 'general')
                else:
                    option['tab'] = section
                    option['subtab'] = old_tab
                option['_locale_domain'] = domain
                option['_use_locale'] = True
                plugin.options[key] = option
        plugin.add_cmd('python_exec', instruction='Execute Python code. Execution is non-interactive.',
                       params=[{'name': 'code', 'type': 'str', 'required': True,
                                'description': 'Python code to execute'}],
                       tab='python', subtab='general',
                       description='Executes Python code using the selected interpreter and runtime.',
                       _locale_domain='plugin.filesystem', _use_locale=True)
        plugin.add_cmd('python_kernel_restart', instruction='Restart the current IPython kernel and clear its state.',
                       params=[], tab='python', subtab='general',
                       description='Restarts the IPython kernel and clears its variables and execution state. '
                                   'Available only when IPython is enabled.',
                       _locale_domain='plugin.filesystem', _use_locale=True)
        plugin.options['cmd.shell_exec']['value']['instruction'] = (
            'Execute a system command in the shared runtime. Execution is non-interactive; '
            'supply all options and answers in the command. The current working directory '
            'is set automatically. Use this tool for shell commands and package installation.')
        plugin.add_option('custom_sandbox_path', type='text', value='',
                          label='Custom sandbox path',
                          description='Custom directory used to build and load the Built-in sandbox. Leave empty to use the default directory.',
                          tab='runtime', subtab='builtin_sandbox', _locale_domain='plugin.filesystem', _use_locale=True)
        plugin.add_option('native_packages', type='textarea',
                          value='\n'.join(NativeTools.default_packages()),
                          label='System packages (Pixi)',
                          description='System packages installed by Pixi in the Built-in sandbox, not on the host. Enter one conda-forge package name per line. Rebuild the sandbox to apply changes. Leave empty to install no system packages.',
                          tab='runtime', subtab='builtin_sandbox', _locale_domain='plugin.filesystem', _use_locale=True)
        # Runtime is the first top-level tab; its General subtab comes first.
        plugin.options = dict(sorted(plugin.options.items(), key=lambda item: (
            list(plugin.tabs).index(item[1]['tab']),
            0 if item[1].get('subtab') in ('general', 'runtime') else
            (1 if item[1].get('subtab') in ('delivery', 'builtin_sandbox') else 2))))
