"""Provider-owned remote tools: migration, settings and native payload contracts."""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from packaging.version import Version

from pygpt_net.config import Config
from pygpt_net.core.llm.llm import LLM
from pygpt_net.core.settings.settings import Settings
from pygpt_net.controller.chat.remote_tools import RemoteTools
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.provider.core.config.patch import Patch
from pygpt_net.provider.core.config.patches.patch_before_2_8_35 import migrate_remote_tools, metadata_providers


def window_with_providers(data=None):
    cfg = object.__new__(Config)
    cfg.data = copy.deepcopy(data or {})
    cfg.save = MagicMock()
    window = SimpleNamespace(core=SimpleNamespace(config=cfg, updater=MagicMock()),
                             ui=SimpleNamespace(nodes={'input': MagicMock()}))
    window.core.llm = LLM(window)
    for provider in metadata_providers():
        window.core.llm.register(provider.id, provider)
    window.controller = SimpleNamespace(chat=SimpleNamespace(remote_tools=RemoteTools(window)))
    return window


def test_migration_preserves_false_empty_json_advanced_and_existing_values():
    data = {
        'remote_tools.web_search': False,
        'remote_tools.mcp.args': '{"server_url":"private"}',
        'remote_tools.google.file_search.args': '',
        'remote_tools.anthropic.web_search.max_uses': 7,
        'remote_tools.xai.web.allowed_websites': ['example.org'],
        'remote_tools.xai.return_citations': False,
        'remote_tools.anthropic.retired': {'custom': 1},
        'remote_tools.computer_use.env': 'browser',
        'remote_tools.computer_use.sandbox': True,
        'remote_tools.global.web_search': False,
        'providers': {'openai': {'api_key': 'secret', 'remote_tools': {'web_search': True}}},
    }
    assert migrate_remote_tools(data)
    p = data['providers']
    assert p['openai']['api_key'] == 'secret'
    assert p['openai']['remote_tools']['web_search'] is True
    assert p['openai']['remote_tools']['mcp.args'] == '{"server_url":"private"}'
    assert p['google']['remote_tools']['file_search.args'] == ''
    assert p['anthropic']['remote_tools']['web_search.max_uses'] == 7
    assert p['anthropic']['remote_tools']['retired'] == {'custom': 1}
    assert p['x_ai']['remote_tools']['web.allowed_websites'] == ['example.org']
    assert p['x_ai']['remote_tools']['return_citations'] is False
    assert data['computer_use.sandbox'] is True
    assert data['computer_use.env'] == 'browser'
    assert [k for k in data if k.startswith('remote_tools.')] == ['remote_tools.global.web_search']
    before = copy.deepcopy(data)
    assert not migrate_remote_tools(data)
    assert data == before


def test_patch_2835_runs_migration_and_saves(tmp_path):
    window = window_with_providers({'__meta__': {'version': '2.8.34'}, 'remote_tools.image': True})
    window.core.config.path = str(tmp_path)
    window.core.config.get_base_workdir = lambda: str(tmp_path)
    window.core.packages = MagicMock()
    assert Patch(window).execute(Version('2.8.35'))
    assert window.core.llm.get('openai').is_remote_tool_enabled('image')
    assert 'remote_tools.image' not in window.core.config.data
    window.core.config.save.assert_called_once()


def test_new_provider_needs_only_setup_for_settings_storage_and_global_toggle():
    class NewProvider(BaseLLM):
        def setup(self):
            return {'remote_tools': {
                'web_search': {'type': 'bool', 'default': False, 'label': 'Search', 'tool': True},
                'web_search.domains': {'type': 'text', 'default': '', 'label': 'Domains'},
            }}
    window = window_with_providers()
    provider = NewProvider()
    provider.id, provider.name = 'new', 'New provider'
    window.core.llm.register('new', provider)
    assert provider.sync_config()
    assert not provider.sync_config()
    options = window.core.llm.get_settings_options()
    option = options['provider.new.remote_tools.web_search']
    assert option['section'] == 'remote_tools'
    assert option['_tab_label'] == 'New provider'
    assert option['_remote_tool_key'] == 'web_search'
    assert not option['_use_locale']
    assert set(provider.get_remote_tools()) == {'web_search'}
    window.controller.chat.remote_tools.toggle('web_search')
    assert provider.is_remote_tool_enabled('web_search')
    assert window.core.config.data['providers']['new']['remote_tools']['web_search'] is True
    assert provider.supports_remote_tool(SimpleNamespace(id='future-model'), 'web_search')
    assert not provider.supports_remote_tool(SimpleNamespace(id='future-model'), 'missing')


@pytest.mark.parametrize('provider,blocked,future', [
    ('openai', 'gpt-4-turbo', 'gpt-99'), ('google', 'gemini-1.0-pro', 'gemini-99'),
    ('anthropic', 'claude-3-5-sonnet', 'claude-99'), ('x_ai', 'grok-3', 'grok-99'),
])
def test_provider_capability_policy(provider, blocked, future):
    window = window_with_providers()
    remote = window.controller.chat.remote_tools
    assert not remote.supported(SimpleNamespace(provider=provider, id=blocked), 'web_search')
    assert remote.supported(SimpleNamespace(provider=provider, id=future), 'web_search')


def test_settings_defaults_reset_tools_without_resetting_api_credentials():
    window = window_with_providers()
    cfg = window.core.config
    cfg.initialized_base = True
    cfg.data_base = {'providers': {}}
    window.core.llm.sync_provider_configs()
    p = window.core.llm.get('openai')
    p.set_config('api_key', 'secret')
    p.set_remote_tool_enabled('image', True)
    p.set_remote_tool_config('mcp.args', 'custom')
    settings = Settings(window)
    settings.options = window.core.llm.get_settings_options()
    settings.initialized = True
    settings.load_app_settings()
    assert p.get_config('api_key') == 'secret'
    assert not p.is_remote_tool_enabled('image')
    assert p.get_remote_tool_config('mcp.args') == p.get_remote_tools_schema()['mcp.args']['default']


def test_anthropic_payload_uses_provider_flags_and_parameters():
    from pygpt_net.provider.api.anthropic.remote_tools import RemoteTools as Builder
    window = window_with_providers()
    provider = window.core.llm.get('anthropic')
    provider.set_remote_tool_enabled('web_fetch', True)
    provider.set_remote_tool_config('web_fetch.max_uses', 3)
    provider.set_remote_tool_config('web_search.allowed_domains', 'example.org, example.com')
    tools = Builder(window).build_remote_tools(SimpleNamespace(provider='anthropic', id='claude-future'))
    search = next(t for t in tools if t['name'] == 'web_search')
    fetch = next(t for t in tools if t['name'] == 'web_fetch')
    assert search['allowed_domains'] == ['example.org', 'example.com']
    assert fetch['max_uses'] == 3


def test_xai_legacy_and_responses_payloads_use_provider_parameters():
    from pygpt_net.provider.api.x_ai.remote_tools import Remote
    window = window_with_providers()
    provider = window.core.llm.get('x_ai')
    provider.set_remote_tool_config('web.allowed_websites', 'example.org')
    provider.set_remote_tool_config('return_citations', False)
    model = SimpleNamespace(provider='x_ai', id='grok-future')
    builder = Remote(window)
    result = builder.build(model)
    assert result['http']['return_citations'] is False
    assert result['http']['sources'][0]['allowed_websites'] == ['example.org']
    result = builder.build_for_responses(model)
    assert result['tools'][0]['filters']['allowed_domains'] == ['example.org']


def test_google_payload_uses_provider_flags_and_store_ids():
    from pygpt_net.provider.api.google.remote_tools import RemoteTools as Builder
    window = window_with_providers()
    provider = window.core.llm.get('google')
    provider.set_remote_tool_enabled('file_search', True)
    provider.set_remote_tool_config('file_search.args', 'stores/one, stores/two')
    model = SimpleNamespace(provider='google', id='gemini-future')
    tools = Builder(window).build_remote_tools(model)
    file_tool = next(t for t in tools if t.file_search is not None)
    assert file_tool.file_search.file_search_store_names == ['stores/one', 'stores/two']


def test_no_flat_provider_tool_reads_or_static_settings_remain():
    root = Path(__file__).parents[3] / 'src' / 'pygpt_net'
    settings = json.loads((root / 'data/config/settings.json').read_text())
    assert not any(k.startswith('remote_tools.') for k in settings)
    for path in root.rglob('*.py'):
        if 'patch' in str(path):
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                assert not (arg.value.startswith('remote_tools.')
                            and not arg.value.startswith('remote_tools.global.')
                            and isinstance(node.func, ast.Attribute)
                            and node.func.attr in ('get', 'set')), (path, arg.value)


def test_settings_editor_round_trips_provider_values_and_nullable_switches(monkeypatch):
    from pygpt_net.controller.settings.editor import Editor
    monkeypatch.setattr("pygpt_net.controller.settings.editor.trans", lambda text: text)
    window = window_with_providers()
    window.ui = MagicMock()
    window.controller = MagicMock()
    window.update_status = MagicMock()
    window.core.idx = MagicMock()
    window.core.config.setup_env = MagicMock()
    window.dispatch = MagicMock()
    provider = window.core.llm.get('x_ai')
    provider.set_remote_tool_config('web.safe_search', False)
    provider.set_remote_tool_config('web.allowed_websites', ['example.org', 'example.com'])
    window.core.llm.get('anthropic').set_remote_tool_config('mcp.tools', [{'type': 'mcp_toolset'}])
    editor = Editor(window)
    editor.config_changed = MagicMock(return_value=False)
    editor.options = {key: value for key, value in window.core.llm.get_settings_options().items()
                      if value['section'] == 'remote_tools'}
    editor.init('settings')
    key = 'provider.x_ai.remote_tools.web.safe_search'
    assert editor.options[key]['value'] == 'false'
    assert editor.options[key]['keys'] == [{'': 'Default'}, {'true': 'Enabled'}, {'false': 'Disabled'}]
    assert editor.options['provider.x_ai.remote_tools.web.allowed_websites']['value'] == 'example.org, example.com'
    assert json.loads(editor.options['provider.anthropic.remote_tools.mcp.tools']['value']) == [{'type': 'mcp_toolset'}]
    values = {k: v['value'] for k, v in editor.options.items()}
    values[key] = ''
    values['provider.openai.remote_tools.mcp.args'] = '{"server_url":"https://example.org"}'
    window.controller.config.get_value.side_effect = lambda **kwargs: values[kwargs['key']]
    editor.save('settings')
    assert provider.get_remote_tool_config('web.safe_search') is None
    assert window.core.llm.get('openai').get_remote_tool_config('mcp.args') == '{"server_url":"https://example.org"}'
    assert not any(k.startswith('provider.') for k in window.core.config.data)


def test_localized_provider_labels_and_ids_match_generated_options():
    window = window_with_providers()
    options = window.core.llm.get_settings_options()
    for provider in window.core.llm.llms.values():
        for key, field in provider.get_remote_tools_schema().items():
            if field.get('hidden'):
                continue
            option_id = window.core.llm.get_settings_option_id(provider.id, 'remote_tools.' + key)
            option = options[option_id]
            assert option['label'] == field['label']
            assert option['description'] == field['desc']
            assert option['_use_locale'] == field['use_locale']
            if field['use_locale']:
                locale = Path(__file__).parents[3] / 'src/pygpt_net/data/locale/locale.en.ini'
                text = locale.read_text()
                assert field['label'] + ' =' in text or field['label'] + '=' in text


def test_config_sync_preserves_values_and_provider_isolation():
    window = window_with_providers({'providers': {'openai': {'remote_tools': {'mcp': True, 'mcp.args': ''}}}})
    assert window.core.llm.sync_provider_configs()
    assert not window.core.llm.sync_provider_configs()
    openai = window.core.llm.get('openai')
    google = window.core.llm.get('google')
    assert openai.is_remote_tool_enabled('mcp')
    assert not google.is_remote_tool_enabled('mcp')
    assert openai.get_remote_tool_config('mcp.args') == ''
    assert google.get_remote_tool_config('mcp.args') != ''
