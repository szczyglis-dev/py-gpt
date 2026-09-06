from unittest.mock import MagicMock, patch

from pygpt_net.controller.plugins.settings import Settings


def _settings():
    window = MagicMock()
    window.ui.tabs = {}
    window.core.plugins.plugins = {}
    return Settings(window), window


def test_plugin_settings_setup_preserves_current_tab_index_when_available():
    ctrl, window = _settings()
    tab = MagicMock()
    tab.currentIndex.return_value = 4
    window.ui.tabs['plugin.settings'] = tab
    ctrl.setup()
    window.plugin_settings.setup.assert_called_once_with(4)


def test_plugin_settings_open_initializes_once_with_qt_processing_mocked():
    ctrl, window = _settings()
    ctrl.setup = MagicMock()
    ctrl.init = MagicMock()
    freeze = MagicMock()
    freeze.__enter__.return_value = None
    freeze.__exit__.return_value = None
    with patch('pygpt_net.controller.plugins.settings.QApplication.processEvents'), \
         patch('pygpt_net.controller.plugins.settings.freeze_updates', return_value=freeze):
        ctrl.open()
        ctrl.open()
    ctrl.setup.assert_called_once_with()
    ctrl.init.assert_called_once_with()
    window.ui.dialogs.open.assert_called_once_with('plugin_settings', width=800, height=500)
    assert ctrl.config_initialized is True
    assert ctrl.config_dialog is True


def test_plugin_settings_init_loads_each_plugin_options_and_selects_first():
    ctrl, window = _settings()
    p1, p2 = MagicMock(), MagicMock()
    p1.setup.return_value = {'a': {'value': 1}}
    p2.setup.return_value = {'b': {'value': 2}}
    window.core.plugins.plugins = {'one': p1, 'two': p2}

    ctrl.init()

    assert ctrl.current_plugin == 'one'
    assert window.controller.config.load_options.call_count == 2
    window.controller.layout.restore_plugin_settings.assert_called_once_with()


def test_plugin_settings_refresh_option_ignores_unknowns_and_updates_known_option():
    ctrl, window = _settings()
    plugin = MagicMock()
    option = {'keys': {'x': 'X'}}
    plugin.options = {'choice': option}
    window.core.plugins.plugins = {'plug': plugin}

    ctrl.refresh_option('missing', 'choice')
    ctrl.refresh_option('plug', 'missing')
    window.controller.config.update_list.assert_not_called()

    ctrl.refresh_option('plug', 'choice')
    window.controller.config.placeholder.apply.assert_called_once_with(option)
    window.controller.config.update_list.assert_called_once_with(
        option=option, parent_id='plugin.plug', key='choice', items={'x': 'X'}
    )


def test_plugin_settings_save_persists_values_removes_stale_and_dispatches_event():
    ctrl, window = _settings()
    ctrl.config_dialog = True
    plugin = MagicMock()
    plugin.setup.return_value = {'enabled': {'type': 'bool'}}
    plugin.options = {'enabled': {'value': False}}
    window.core.plugins.plugins = {'plug': plugin}
    window.core.config.data = {'plugins': {'stale': {'x': 1}}}
    window.controller.config.get_value.return_value = True

    ctrl.save()

    assert window.core.config.data['plugins'] == {'plug': {'enabled': True}}
    assert plugin.options['enabled']['value'] is True
    window.controller.plugins.presets.save_current.assert_called_once_with()
    window.core.config.save.assert_called_once_with()
    window.ui.dialogs.close.assert_called_once_with('plugin_settings')
    window.controller.ui.update_tokens.assert_called_once_with()


def test_plugin_settings_defaults_confirm_or_apply():
    ctrl, window = _settings()
    ctrl.init = MagicMock()
    ctrl.load_defaults_user(False)
    window.ui.dialogs.confirm.assert_called_once()
    ctrl.load_defaults_user(True)
    ctrl.init.assert_called_once_with()

    ctrl.init.reset_mock()
    ctrl.current_plugin = 'plug'
    ctrl.load_defaults_app(True)
    window.core.plugins.restore_options.assert_called_once_with('plug')
    ctrl.init.assert_called_once_with()
    window.ui.dialogs.alert.assert_called_once()


def test_plugin_settings_get_option_and_toggle_close():
    ctrl, window = _settings()
    window.core.plugins.plugins = {'p': MagicMock(options={'x': 7})}
    assert ctrl.get_option('p', 'x') == 7
    ctrl.config_dialog = True
    ctrl.toggle_editor()
    window.ui.dialogs.close.assert_called_once_with('plugin_settings')


def test_plugin_settings_open_plugin_sets_current_then_opens():
    ctrl, _ = _settings()
    ctrl.open = MagicMock()
    ctrl.open_plugin('plug')
    assert ctrl.current_plugin == 'plug'
    ctrl.open.assert_called_once_with()
