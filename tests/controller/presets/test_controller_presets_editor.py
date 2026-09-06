from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.presets.editor import Editor


def _editor():
    window = MagicMock()
    window.ui.tabs = {
        'preset.editor.tabs': MagicMock(),
        'preset.editor.extra': MagicMock(),
    }
    window.ui.nodes = {'preset.editor.avatar': MagicMock()}
    return Editor(window), window


def test_preset_editor_options_and_noop_mode_visibility_method():
    ctrl, _ = _editor()
    assert ctrl.get_options() is ctrl.options
    assert ctrl.get_option('name') is ctrl.options['name']
    assert ctrl.show_hide_by_mode() is None


def test_preset_editor_setup_refreshes_dynamic_lists_and_registers_hooks():
    ctrl, window = _editor()
    ctrl.update_models_list = MagicMock()
    ctrl.append_extra_config = MagicMock()
    ctrl.update_providers_list = MagicMock()
    ctrl.setup()
    ctrl.update_models_list.assert_called_once_with()
    ctrl.append_extra_config.assert_called_once_with()
    ctrl.update_providers_list.assert_called_once_with()
    assert window.ui.add_hook.call_count == 3


def test_preset_editor_to_current_copies_selected_personalization_values():
    ctrl, window = _editor()
    preset = SimpleNamespace(ai_name='AI', user_name='User', prompt='Prompt', temperature=0.7)
    ctrl.to_current(preset)
    assert window.core.config.set.call_args_list == [
        (('ai_name', 'AI'), {}),
        (('user_name', 'User'), {}),
        (('prompt', 'Prompt'), {}),
        (('temperature', 0.7), {}),
    ]


def test_preset_editor_from_current_applies_all_global_values_to_editor():
    ctrl, window = _editor()
    values = {
        'ai_name': 'AI', 'user_name': 'User', 'prompt': 'P',
        'temperature': 1.2, 'model': 'm1',
    }
    window.core.config.get.side_effect = lambda key: values[key]
    ctrl.from_current()
    calls = window.controller.config.apply_value.call_args_list
    assert [c.kwargs['key'] for c in calls] == [
        'ai_name', 'user_name', 'prompt', 'temperature', 'model'
    ]
    assert calls[-1].kwargs['value'] == 'm1'


def test_preset_editor_update_from_global_updates_current_preset_and_saves():
    ctrl, window = _editor()
    preset = SimpleNamespace(user_name='Old', ai_name='OldAI')
    window.core.config.get.return_value = 'preset-1'
    window.core.presets.items = {'preset-1': preset}
    ctrl.update_from_global('preset.user_name', 'New')
    assert preset.user_name == 'New'
    window.core.config.set.assert_called_once_with('user_name', 'New')
    window.core.presets.save.assert_called_once_with('preset-1')


def test_preset_editor_toggle_tab_updates_qt_tab_and_expert_counter():
    ctrl, window = _editor()
    ctrl.experts.update_tab = MagicMock()
    tabs = window.ui.tabs['preset.editor.tabs']
    ctrl.toggle_tab('experts', True)
    tabs.setTabEnabled.assert_called_with(ctrl.TAB_IDX['experts'], True)
    tabs.setTabVisible.assert_called_with(ctrl.TAB_IDX['experts'], True)
    ctrl.experts.update_tab.assert_called_once_with()
    ctrl.toggle_tab('experts', False)
    tabs.setTabEnabled.assert_called_with(ctrl.TAB_IDX['experts'], False)
    tabs.setTabVisible.assert_called_with(ctrl.TAB_IDX['experts'], False)


def test_preset_editor_remove_avatar_requires_confirmation_when_not_forced():
    ctrl, window = _editor()
    ctrl.remove_avatar(False)
    window.ui.dialogs.confirm.assert_called_once()
    window.ui.nodes['preset.editor.avatar'].remove_avatar.assert_not_called()


def test_preset_editor_remove_avatar_mocks_filesystem_calls():
    ctrl, window = _editor()
    ctrl.current = 'uuid'
    preset = SimpleNamespace(ai_avatar='avatar.png')
    window.core.presets.get_by_uuid.return_value = preset
    window.core.config.get_user_dir.return_value = '/presets'
    with patch('pygpt_net.controller.presets.editor.os.path.exists', return_value=True), \
         patch('pygpt_net.controller.presets.editor.os.remove') as remove:
        ctrl.remove_avatar(True)
    assert remove.call_count == 2
    assert preset.ai_avatar == ''
    window.ui.nodes['preset.editor.avatar'].remove_avatar.assert_called_once_with()
    window.controller.config.apply_value.assert_called_once_with(
        parent_id='preset', key='ai_avatar', option=ctrl.options['ai_avatar'], value=''
    )


def test_preset_editor_update_avatar_config_prefers_existing_thumbnail_without_real_image_io():
    ctrl, window = _editor()
    window.core.config.get_user_dir.return_value = '/presets'
    preset = SimpleNamespace(ai_avatar='avatar.png')
    with patch('pygpt_net.controller.presets.editor.os.path.exists', side_effect=lambda p: True):
        ctrl.update_avatar_config(preset)
    widget = window.ui.nodes['preset.editor.avatar']
    widget.load_avatar.assert_called_once_with('/presets/avatars/thumb_avatar.png')
    widget.enable_remove_button.assert_called_once_with(True)


def test_preset_editor_toggle_extra_options_hides_agent_tabs_outside_agent_modes():
    ctrl, window = _editor()
    ctrl.tab_options_idx = {'agent-x': [1, 2]}
    tabs = window.ui.tabs['preset.editor.extra']
    tabs.count.return_value = 3
    window.core.config.get.return_value = 'chat'
    ctrl.toggle_extra_options()
    tabs.setTabVisible.assert_any_call(0, True)
    tabs.setTabVisible.assert_any_call(1, False)
    tabs.setTabVisible.assert_any_call(2, False)


def test_preset_editor_toggle_extra_options_by_provider_shows_base_when_mapping_empty():
    ctrl, window = _editor()
    ctrl.tab_options_idx = {}
    tabs = window.ui.tabs['preset.editor.extra']
    ctrl.toggle_extra_options_by_provider()
    tabs.setTabVisible.assert_called_once_with(0, True)


def test_preset_editor_load_extra_options_applies_saved_agent_values():
    from pygpt_net.core.types import MODE_AGENT_OPENAI

    ctrl, window = _editor()
    window.ui.config = {'agent.agent-x.main': {}}
    window.core.config.get.return_value = MODE_AGENT_OPENAI
    agent = MagicMock()
    agent.get_options.return_value = {
        'main': {'options': {'temperature': {'type': 'float', 'default': 0.1}}}
    }
    window.core.agents.provider.get.return_value = agent
    preset = SimpleNamespace(
        agent_provider_openai='agent-x', agent_provider=None,
        extra={'agent-x': {'main': {'temperature': 0.8}}},
    )
    ctrl._apply_combo_defaults_for_group = MagicMock()

    ctrl.load_extra_options(preset)

    window.controller.config.apply_value.assert_called_once_with(
        parent_id='agent.agent-x.main', key='temperature',
        option={'type': 'float', 'default': 0.1}, value=0.8,
    )
    ctrl._apply_combo_defaults_for_group.assert_called_once()


def test_preset_editor_load_extra_defaults_applies_schema_defaults():
    from pygpt_net.core.types import MODE_AGENT_OPENAI

    ctrl, window = _editor()
    ctrl.tab_options_idx = {'agent-x': [1]}
    window.core.config.get.return_value = MODE_AGENT_OPENAI
    window.ui.config = {'agent.agent-x.main': {}}
    agent = MagicMock()
    agent.get_options.return_value = {
        'main': {'options': {'x': {'type': 'text', 'default': 'default'}}}
    }
    window.core.agents.provider.get.return_value = agent
    ctrl._apply_combo_defaults_for_group = MagicMock()

    ctrl.load_extra_defaults()

    window.controller.config.apply_value.assert_called_once_with(
        parent_id='agent.agent-x.main', key='x',
        option={'type': 'text', 'default': 'default'}, value='default',
    )


def test_preset_editor_load_extra_defaults_current_does_not_overwrite_nonempty_value():
    from pygpt_net.core.types import MODE_AGENT_OPENAI

    ctrl, window = _editor()
    ctrl.tab_options_idx = {'other': [1]}
    ctrl.current = 'uuid'
    window.core.config.get.return_value = MODE_AGENT_OPENAI
    preset = SimpleNamespace(agent_provider_openai='current', agent_provider=None)
    window.core.presets.get_by_uuid.return_value = preset
    window.ui.config = {'agent.other.main': {}}
    agent = MagicMock()
    agent.get_options.return_value = {
        'main': {'options': {'x': {'type': 'text', 'default': 'default'}}}
    }
    window.core.agents.provider.get.return_value = agent
    window.controller.config.get_value.return_value = 'already-set'
    ctrl._apply_combo_defaults_for_group = MagicMock()

    ctrl.load_extra_defaults_current()

    window.controller.config.apply_value.assert_not_called()


def test_preset_editor_append_extra_options_serializes_dynamic_agent_config():
    from pygpt_net.core.types import MODE_AGENT_OPENAI

    ctrl, window = _editor()
    window.core.config.get.return_value = MODE_AGENT_OPENAI
    window.ui.config = {'agent.agent-x.main': {}}
    agent = MagicMock()
    agent.get_options.return_value = {
        'main': {'options': {'x': {'type': 'text'}}},
        '__prompt__': {'options': {'ignored': {'type': 'text'}}},
    }
    window.core.agents.provider.get.return_value = agent
    window.controller.config.get_value.return_value = 'value'
    preset = SimpleNamespace(agent_provider_openai='agent-x', agent_provider=None, extra=None)

    ctrl.append_extra_options(preset)

    assert preset.extra == {'agent-x': {'main': {'x': 'value'}}}


def test_preset_editor_update_custom_agent_options_returns_cleanly_without_tabs():
    ctrl, window = _editor()
    window.ui.tabs['preset.editor.extra'] = None
    assert ctrl.update_custom_agent_options('agent-x') is None


def test_preset_editor_append_default_prompt_uses_provider_default():
    from pygpt_net.core.types import MODE_AGENT_OPENAI

    ctrl, window = _editor()
    window.core.config.get.return_value = MODE_AGENT_OPENAI
    window.controller.config.get_value.return_value = 'agent-x'
    agent = MagicMock()
    agent.get_default_prompt.return_value = 'Default agent prompt'
    window.core.agents.provider.get.return_value = agent

    ctrl.append_default_prompt()

    window.controller.config.apply_value.assert_called_once_with(
        parent_id='preset', key='prompt', option=ctrl.options['prompt'],
        value='Default agent prompt',
    )


def test_preset_editor_update_indexes_list_refreshes_schema_and_widget():
    ctrl, window = _editor()
    widget = MagicMock()
    window.ui.config = {'preset': {'idx': widget}}
    window.controller.config.placeholder.apply_by_id.return_value = {'_': 'None', 'idx1': 'Index 1'}
    ctrl.update_indexes_list()
    assert ctrl.options['idx']['keys'] == {'_': 'None', 'idx1': 'Index 1'}
    widget.set_keys.assert_called_once_with({'_': 'None', 'idx1': 'Index 1'}, lock=True)


def test_preset_editor_hook_update_routes_prompt_and_provider_changes():
    ctrl, window = _editor()
    window.core.config.get.return_value = 'chat'
    ctrl.toggle_extra_options_by_provider = MagicMock()
    ctrl.append_default_prompt = MagicMock()
    ctrl.load_extra_defaults_current = MagicMock()

    ctrl.hook_update('prompt', 'new prompt', None)
    window.core.config.set.assert_called_once_with('prompt', 'new prompt')
    window.controller.presets.from_global.assert_called_once_with()

    ctrl.hook_update('agent_provider', 'agent-x', None)
    ctrl.toggle_extra_options_by_provider.assert_called_once_with()
    ctrl.append_default_prompt.assert_called_once_with()
    ctrl.load_extra_defaults_current.assert_called_once_with()


def test_preset_editor_edit_resolves_index_and_opens_editor():
    ctrl, window = _editor()
    window.core.config.get.return_value = 'chat'
    preset = MagicMock()
    window.core.presets.get_by_idx.return_value = preset
    ctrl.init = MagicMock()
    ctrl.edit(4)
    window.core.presets.get_by_idx.assert_called_once_with(4, 'chat')
    ctrl.init.assert_called_once_with(preset)
    window.ui.dialogs.open_editor.assert_called_once_with('editor.preset.presets', 4, width=800)


def test_preset_editor_reload_all_optionally_rebuilds_dynamic_options():
    ctrl, _ = _editor()
    ctrl.update_providers_list = MagicMock()
    ctrl.reload_all_custom_agent_options = MagicMock()
    ctrl.init = MagicMock()
    ctrl.opened = True
    ctrl.current_id = 'p1'
    ctrl.reload_all(True)
    ctrl.update_providers_list.assert_called_once_with()
    ctrl.reload_all_custom_agent_options.assert_called_once_with()
    ctrl.init.assert_called_once_with('p1')


def test_preset_editor_init_new_chat_preset_uses_mocked_dynamic_helpers():
    from pygpt_net.core.types import MODE_CHAT

    ctrl, window = _editor()
    window.ui.config = {
        'preset': {'idx': MagicMock(), 'model': MagicMock(), 'name': MagicMock()}
    }
    window.core.config.get.side_effect = lambda key: {'mode': MODE_CHAT, 'model': 'm1'}.get(key)
    for name in [
        'reload_all', 'load_extra_defaults', 'update_indexes_list', 'load_extra_options',
        'toggle_extra_options', 'update_avatar_config', 'show_hide_by_mode',
        'toggle_extra_options_by_provider', 'append_default_prompt',
    ]:
        setattr(ctrl, name, MagicMock())
    ctrl.experts.update_list = MagicMock()

    ctrl.init(None)

    assert ctrl.opened is True
    assert ctrl.current is None
    window.controller.config.load_options.assert_called_once()
    window.ui.config['preset']['idx'].set_value.assert_called_once_with('_')
    window.ui.config['preset']['model'].set_value.assert_called_once_with('m1')
    window.ui.config['preset']['name'].setFocus.assert_called_once_with()
    ctrl.append_default_prompt.assert_called_once_with()


def test_preset_editor_assign_data_normalizes_name_and_model_and_calls_dynamic_serializers():
    ctrl, window = _editor()
    preset = MagicMock()
    window.core.presets.items = {'p1': preset}
    values = {key: False for key in ctrl.options}
    values.update({'name': '', 'model': '_', 'filename': 'p1'})
    window.controller.config.get_value.side_effect = lambda **kw: values[kw['key']]
    ctrl.append_extra_options = MagicMock()
    ctrl.update_avatar_config = MagicMock()
    with patch('pygpt_net.controller.presets.editor.trans', return_value='Untitled'):
        ctrl.assign_data('p1')
    data = preset.from_dict.call_args.args[0]
    assert data['name'] == 'p1 Untitled'
    assert data['model'] is None
    assert preset.filename == 'p1'
    assert preset.tools == {'function': []}
    ctrl.append_extra_options.assert_called_once_with(preset)
    ctrl.update_avatar_config.assert_called_once_with(preset)


def test_preset_editor_upload_avatar_uses_fixed_clock_and_mocked_image_filesystem():
    import datetime as dt

    ctrl, window = _editor()
    fixed_now = dt.datetime(2025, 1, 2, 3, 4, 5)
    real_datetime = dt.datetime

    class FixedDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now
            return fixed_now.replace(tzinfo=dt.timezone.utc).astimezone(tz)

    preset = SimpleNamespace(filename='preset-name', ai_avatar='')
    ctrl.current = 'uuid'
    window.core.presets.get_by_uuid.return_value = preset
    window.core.config.get_user_dir.return_value = '/presets'
    ctrl._create_avatar_thumbnail = MagicMock(return_value='/presets/avatars/thumb.png')
    expected_stamp = '20250102030405'

    with patch('pygpt_net.controller.presets.editor.datetime.datetime', FixedDateTime), \
         patch('pygpt_net.controller.presets.editor.os.path.exists', return_value=True), \
         patch('pygpt_net.controller.presets.editor.os.makedirs'), \
         patch('pygpt_net.controller.presets.editor.os.remove'), \
         patch('pygpt_net.controller.presets.editor.shutil.copy') as copy_file:
        path = ctrl.upload_avatar('/input/avatar.png')

    expected = f'/presets/avatars/preset-name_{expected_stamp}.png'
    assert path == expected
    copy_file.assert_called_once_with('/input/avatar.png', expected)
    assert preset.ai_avatar == f'preset-name_{expected_stamp}.png'
    window.controller.config.apply_value.assert_called_once()


def test_preset_editor_reload_all_custom_agent_options_returns_without_tabs():
    ctrl, window = _editor()
    window.ui.tabs['preset.editor.extra'] = None
    assert ctrl.reload_all_custom_agent_options() is None
