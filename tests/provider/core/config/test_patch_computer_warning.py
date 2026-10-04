from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from packaging.version import Version

from pygpt_net.provider.core.config.patch import Patch


@pytest.mark.parametrize('existing', [None, False, True])
def test_computer_warning_migration_defaults_to_true_and_preserves_preferences(existing):
    data = {'__meta__': {'version': '2.8.37'}}
    if existing is not None:
        data['security.computer.show_warning'] = existing
    config = SimpleNamespace(all=lambda: data, save=Mock())
    updater = Mock()
    updater.post_check_config.return_value = False
    window = SimpleNamespace(core=SimpleNamespace(config=config, updater=updater))
    assert Patch(window).execute(Version('2.8.38'))
    assert config.data['security.computer.show_warning'] is (True if existing is None else existing)
    config.save.assert_called_once_with()
