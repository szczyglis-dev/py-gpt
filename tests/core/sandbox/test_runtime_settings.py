from types import SimpleNamespace

from pygpt_net.core.sandbox.builtin import BuiltinSandboxRuntime
from pygpt_net.core.sandbox.native_tools import NativeTools
from pygpt_net.plugin.filesystem import Plugin


def test_custom_root_is_used_for_build_and_load_and_can_be_cleared(tmp_path):
    config = SimpleNamespace(get_base_workdir=lambda: str(tmp_path / 'default'))
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    values = {'path': ''}
    runtime = BuiltinSandboxRuntime(window, 'python', sandbox_path_provider=lambda: values['path'])
    assert runtime.sandbox_root == str(tmp_path / 'default' / 'sandbox')
    values['path'] = str(tmp_path / 'custom')
    assert runtime.venv_root == str(tmp_path / 'custom' / 'python')
    assert runtime.python_bin.startswith(runtime.venv_root)
    assert runtime.native_tools().root == tmp_path / 'custom' / 'tools'
    values['path'] = ''
    assert runtime.sandbox_root == str(tmp_path / 'default' / 'sandbox')


def test_runtime_settings_defaults_and_pixi_package_selection(tmp_path):
    plugin = Plugin()
    builtin = [key for key, option in plugin.options.items()
               if option['tab'] == 'runtime' and option.get('subtab') == 'builtin_sandbox']
    assert builtin[-2:] == ['custom_sandbox_path', 'native_packages']
    assert plugin.options['custom_sandbox_path']['value'] == ''
    assert plugin.options['native_packages']['value'].splitlines() == list(NativeTools.default_packages())
    tools = NativeTools(tmp_path, packages=['git', 'poppler', 'jq', 'git', 'imagemagick'])
    assert tools.get_packages() == ('git', 'poppler', 'jq', 'imagemagick')
    assert set(tools.get_commands()) == {'git', 'pdftotext', 'pdfinfo', 'jq'}
    assert tools._spec()['packages'] == list(tools.get_packages())
    empty = NativeTools(tmp_path, packages=[])
    assert empty.ensure_optional() is False
    assert empty.bin_dirs() == []
