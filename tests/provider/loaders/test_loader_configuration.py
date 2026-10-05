import configparser
import importlib
from pathlib import Path

from pygpt_net.provider.loaders import base


def test_every_builtin_loader_has_complete_localized_field_schema():
    root = Path(base.__file__).parent
    sources = sorted(list(root.glob('web_*/__init__.py')) + list(root.glob('file_*/__init__.py')))
    assert len(sources) == 29
    for source in sources:
        loader = importlib.import_module('pygpt_net.provider.loaders.' + source.parent.name).Loader()
        ini = configparser.RawConfigParser()
        ini.read(Path(loader.locale_dir) / 'locale.en.ini')
        translations = dict(ini.items('LOCALE'))
        assert loader.locale_domain == 'loader.' + loader.id
        for key in loader.init_args:
            assert translations[loader.init_args_labels[key]]
            assert translations[loader.init_args_desc[key]]
            assert isinstance(loader.init_args_required[key], bool)
        for item in loader.instructions:
            for instruction in item.values():
                for meta in instruction['args'].values():
                    assert translations[meta['label']]
                    assert translations[meta['description']]
                    assert isinstance(meta['required'], bool)


def test_loader_locale_filename_fallback_and_runtime_switch(tmp_path):
    from unittest.mock import MagicMock
    from pygpt_net.core.locale import Locale
    domain = 'loader.test_fallback'
    directory = tmp_path / 'locale'
    directory.mkdir()
    (directory / 'locale.en.ini').write_text('[LOCALE]\nconfig.token.label = Token\nconfig.token.desc = Access token\n')
    (directory / 'locale.pl.ini').write_text('[LOCALE]\nconfig.token.label = Token dostępu\n')
    config = MagicMock()
    config.has.return_value = False
    config.get_app_path.return_value = str(tmp_path)
    config.get_base_workdir.return_value = str(tmp_path)
    config.get_user_path.return_value = str(tmp_path)
    Locale.register_domain(domain, str(directory))
    try:
        locale = Locale(domain, config)
        locale.load('pl', domain)
        assert locale.get('config.token.label', domain) == 'Token dostępu'
        assert locale.get('config.token.desc', domain) == 'Access token'
        locale.load('de', domain)
        assert locale.get('config.token.label', domain) == 'Token'
        assert locale.get('config.token.desc', domain) == 'Access token'
    finally:
        Locale.unregister_domain(domain)


def test_normalize_extended_and_legacy_field_definitions():
    from pygpt_net.provider.loaders.base import normalize_field
    assert normalize_field('bool') == {'type': 'bool', 'extra': {}}
    assert normalize_field('path') == {'type': 'str', 'extra': {'path': True}}
    assert normalize_field({'type': 'secret'}) == {'type': 'str', 'extra': {'secret': True}}
    definition = {'type': 'dict', 'extra': {'secret': True}, 'required': True}
    result = normalize_field(definition)
    assert result == definition
    result['extra']['secret'] = False
    assert definition['extra']['secret'] is True


def test_addon_locale_binding_supplies_standard_keys_and_keeps_explicit_metadata(tmp_path):
    from unittest.mock import MagicMock
    from pygpt_net.core.extensions.extensions import Extensions
    from pygpt_net.core.locale import Locale
    from pygpt_net.provider.loaders.base import BaseLoader
    root = tmp_path / 'addon'
    (root / 'locale').mkdir(parents=True)
    (root / 'locale' / 'locale.en.ini').write_text('[LOCALE]\nconfig.token.label = Token\nconfig.token.desc = Access token\n')
    loader = BaseLoader()
    loader.id = 'addon_demo'
    loader.init_args = {'token': '', 'encoding': 'utf-8'}
    loader.init_args_types = {'token': {'type': 'str', 'extra': {'secret': True}, 'required': True}}
    loader.init_args_labels = {'encoding': 'legacy.encoding.label'}
    loader.instructions = [{'addon_demo': {'args': {'url': {'type': 'str', 'required': True}}}}]
    manager = Extensions(MagicMock())
    try:
        manager._configure_runtime_locale({'_path': str(root), 'id': 'addon_demo', 'type': 'loader'}, [loader])
        assert loader.locale_domain == 'addon.addon_demo'
        assert loader.locale_dir == str(root / 'locale')
        assert loader.init_args_labels['token'] == 'config.token.label'
        assert loader.init_args_labels['encoding'] == 'legacy.encoding.label'
        assert loader.instructions[0]['addon_demo']['args']['url']['required'] is True
        assert loader.instructions[0]['addon_demo']['args']['url']['label'] == 'options.url.label'
    finally:
        Locale.unregister_domain('addon.addon_demo')
