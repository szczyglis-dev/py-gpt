from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from packaging.version import Version
from pygpt_net.provider.core.config.patch import Patch


@pytest.mark.parametrize('expanded', [None, False, True])
@pytest.mark.parametrize('existing', [None, 'left', 'middle', 'right'])
def test_291_toolbox_placement_defaults_to_middle_and_preserves_choice(existing, expanded):
    data = {'__meta__': {'version': '2.9.0'}}
    if existing is not None:
        data['layout.toolbox.placement'] = existing
    if expanded is not None:
        data['layout.toolbox.expanded'] = expanded
    config = SimpleNamespace(all=lambda: data, save=Mock())
    updater = Mock()
    updater.post_check_config.return_value = False
    window = SimpleNamespace(core=SimpleNamespace(config=config, updater=updater))
    assert Patch(window).execute(Version('2.9.1'))
    assert config.data['layout.toolbox.placement'] == (existing or 'middle')
    assert config.data['layout.toolbox.expanded'] is (expanded if expanded is not None else False)
