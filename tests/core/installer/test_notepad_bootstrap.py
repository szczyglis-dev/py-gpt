from types import SimpleNamespace
from unittest.mock import MagicMock

from packaging.version import Version

from pygpt_net.core.installer import Installer
from pygpt_net.core.updater import Updater


def test_install_and_migrate_notepad_before_tools_exist(tmp_path, capsys):
    services = {name: MagicMock() for name in (
        'config', 'models', 'presets', 'idx', 'ctx', 'attachments', 'assistants',
        'image', 'filesystem', 'camera', 'debug')}
    services['config'].path = str(tmp_path / 'profile')
    window = SimpleNamespace(core=SimpleNamespace(**services))
    assert not hasattr(window, 'tools')
    Installer(window).install()
    for name in ('attachments', 'assistants', 'image', 'filesystem', 'camera'):
        services[name].install.assert_called_once_with()
    updater = Updater(window)
    updater.throw_startup_error = MagicMock()
    updater.patch_notepad(Version('2.0.0'))
    updater.throw_startup_error.assert_not_called()
    services['debug'].log.assert_not_called()
    assert 'Error installing config files' not in capsys.readouterr().out
