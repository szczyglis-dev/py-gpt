from types import SimpleNamespace
from unittest.mock import MagicMock

from packaging.version import Version
from pygpt_net.provider.core.model.patch import Patch


def test_new_models_migration_keeps_existing_custom_settings():
    customized = SimpleNamespace(id='gpt-6.1-sol', ctx=42)
    models = SimpleNamespace(items={'gpt-6.1-sol': customized},
                             get_version=lambda: '2.8.37',
                             from_base=lambda key: SimpleNamespace(id=key),
                             save=MagicMock())
    window = SimpleNamespace(core=SimpleNamespace(models=models))
    assert Patch(window).execute(Version('2.8.38'))
    assert models.items['gpt-6.1-sol'] is customized
    assert models.items['grok-4.7'].id == 'grok-4.7'
    assert models.items['claude-opus-5-5'].id == 'claude-opus-5-5'
    models.save.assert_called_once()
    models.save.reset_mock()
    assert not Patch(window).execute(Version('2.8.38'))
    models.save.assert_not_called()
