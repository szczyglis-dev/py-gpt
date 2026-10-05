"""Idempotent migration of global and preset plugin settings for 2.9.1."""
from copy import deepcopy
import re

LEGACY = {'cmd_files': 'filesystem', 'cmd_code_interpreter': 'python', 'cmd_system': 'system'}
TOOLS = {'ipython_exec': 'python_exec', 'ipython_kernel_restart': 'python_kernel_restart',
         'ipython_sys_exec': 'shell_exec', 'python_sys_exec': 'shell_exec',
         'sys_exec': 'shell_exec'}


FILESYSTEM_TOOLS = ('send_file', 'deliver_file_to_user', 'attach_runtime_file', 'runtime_artifacts', 'read_file', 'query_file', 'save_file', 'append_file', 'delete_file', 'list_dir', 'tree', 'mkdir', 'download_file', 'rmdir', 'copy_file', 'copy_dir', 'move', 'is_dir', 'is_file', 'file_exists', 'file_size', 'file_info', 'cwd', 'file_index', 'pack_archive', 'unpack_archive', 'find')


def migrate_filesystem_tools(options):
    """Rename stored tool switches while retaining explicit new settings."""
    changed = False
    if not isinstance(options, dict):
        return changed
    for name in FILESYSTEM_TOOLS:
        old, new = 'cmd.' + name, 'cmd.fs_' + name
        if old in options:
            value = options.pop(old)
            options.setdefault(new, value)
            changed = True
    return changed


def defaults():
    from pygpt_net.plugin.base.plugin import BasePlugin
    from .config import Config
    plugin = BasePlugin()
    Config(plugin).from_defaults(plugin)
    return plugin.options


def migrate_plugin_settings(settings, reset_runtime=False):
    """Merge provider options; Python owns all shared runtime options."""
    if not isinstance(settings, dict) or not any(key in settings for key in LEGACY):
        return False
    options = defaults()
    merged = {}
    shell_enabled = []
    for old, section in LEGACY.items():
        provider = settings.pop(old, {})
        if not isinstance(provider, dict):
            continue
        if old == 'cmd_files':
            migrate_filesystem_tools(provider)
        for key, value in provider.items():
            if key in options:
                owner = options[key]['tab']
                if owner == section or (old == 'cmd_code_interpreter' and owner == 'runtime'):
                    merged[key] = deepcopy(value)
        if old == 'cmd_system' and 'cmd.sys_exec' in provider:
            stored = provider['cmd.sys_exec']
            shell_enabled.append(stored.get('enabled', True) if isinstance(stored, dict) else bool(stored))
        if old == 'cmd_code_interpreter':
            shell = 'cmd.ipython_sys_exec' if provider.get('use_ipython', True) else 'cmd.python_sys_exec'
            if shell in provider:
                stored = provider[shell]
                shell_enabled.append(stored.get('enabled', True) if isinstance(stored, dict) else bool(stored))
            selected = 'cmd.ipython_exec' if provider.get('use_ipython', True) else 'cmd.python_exec'
            if selected in provider:
                merged['cmd.python_exec'] = deepcopy(options['cmd.python_exec']['value'])
                stored = provider[selected]
                merged['cmd.python_exec']['enabled'] = stored.get('enabled', True) if isinstance(stored, dict) else bool(stored)
            if 'cmd.ipython_kernel_restart' in provider:
                merged['cmd.python_kernel_restart'] = provider['cmd.ipython_kernel_restart']
    if shell_enabled:
        merged['cmd.shell_exec'] = any(shell_enabled)
    existing = deepcopy(settings.get('filesystem', {}))
    migrate_filesystem_tools(existing)
    merged.update(existing)
    if reset_runtime:
        for key, option in options.items():
            if option['tab'] == 'runtime' and key != 'sandbox':
                merged[key] = deepcopy(option['value'])
    settings['filesystem'] = merged
    return True


def migrate_tree(data, reset_runtime=False):
    """Handle enabled maps, config maps and arbitrary nested preset containers."""
    if isinstance(data, list):
        changed = False
        for index, value in enumerate(data):
            if isinstance(value, str) and value in LEGACY:
                data[index] = 'filesystem'
                changed = True
            elif isinstance(value, (dict, list)):
                changed |= migrate_tree(value, reset_runtime)
        # Plugin-id lists should not contain duplicate integrated entries.
        if changed and all(isinstance(value, str) for value in data):
            data[:] = list(dict.fromkeys(data))
        return changed
    if not isinstance(data, dict):
        return False
    changed = False
    prompt = data.get('prompt.cmd')
    if isinstance(prompt, str):
        updated = re.sub(r'\bsys_exec\b', 'shell_exec', prompt)
        if updated != prompt:
            data['prompt.cmd'] = updated
            changed = True
    integrated = data.get('filesystem')
    changed |= migrate_filesystem_tools(integrated)
    if isinstance(integrated, dict) and 'cmd.sys_exec' in integrated:
        stored = integrated.pop('cmd.sys_exec')
        if 'cmd.shell_exec' not in integrated:
            integrated['cmd.shell_exec'] = stored
        changed = True
    legacy_values = [data[key] for key in LEGACY if key in data]
    if legacy_values:
        if all(isinstance(value, bool) for value in legacy_values):
            enabled = bool(data.get('filesystem', False)) or any(legacy_values)
            for key in LEGACY:
                data.pop(key, None)
            data['filesystem'] = enabled
            changed = True
        elif any(isinstance(value, dict) for value in legacy_values):
            changed |= migrate_plugin_settings(data, reset_runtime)
    for key, value in list(data.items()):
        if isinstance(value, (dict, list)):
            changed |= migrate_tree(value, reset_runtime)
    return changed
