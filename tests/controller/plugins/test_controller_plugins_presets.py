from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.plugins.presets import Presets


def _presets(data=None):
    window = MagicMock()
    ctrl = Presets(window)
    ctrl.get_presets = MagicMock(return_value=deepcopy(data or {}))
    ctrl.store = MagicMock()
    ctrl.update_list = MagicMock()
    ctrl.update_menu = MagicMock()
    return ctrl, window


def test_plugin_presets_create_rejects_blank_name():
    ctrl, window = _presets()
    ctrl.create('id1', '   ')
    window.update_status.assert_called_once()
    ctrl.store.assert_not_called()


def test_plugin_presets_create_stores_snapshot_and_selects_it():
    ctrl, window = _presets()
    ctrl.current_to_preset = MagicMock()
    ctrl.toggle = MagicMock()
    ctrl.create('id1', 'My preset')
    saved = ctrl.store.call_args.args[0]
    assert saved['id1'] == {'name': 'My preset', 'enabled': {}, 'config': {}}
    ctrl.current_to_preset.assert_called_once_with('id1')
    ctrl.toggle.assert_called_once_with('id1')
    window.ui.dialog['create'].close.assert_called_once_with()


def test_plugin_presets_index_helpers_have_safe_bounds():
    ctrl, _ = _presets({'a': {'name': 'A'}, 'b': {'name': 'B'}})
    assert ctrl.get_id_by_idx(0) == 'a'
    assert ctrl.get_id_by_idx(1) == 'b'
    assert ctrl.get_id_by_idx(-1) is None
    assert ctrl.get_id_by_idx(2) is None


def test_plugin_presets_delete_by_idx_confirms_then_deletes():
    ctrl, window = _presets({'a': {'name': 'A'}})
    ctrl.delete = MagicMock()
    ctrl.delete_by_idx(0, False)
    window.ui.dialogs.confirm.assert_called_once()
    ctrl.delete.assert_not_called()

    ctrl.delete_by_idx(0, True)
    ctrl.delete.assert_called_once_with('a')


def test_plugin_presets_duplicate_creates_independent_copy_with_new_uuid():
    ctrl, _ = _presets({'a': {'name': 'A', 'config': {'x': [1]}}})
    with patch('pygpt_net.controller.plugins.presets.uuid4', return_value='new-id'):
        ctrl.duplicate('a')
    saved = ctrl.store.call_args.args[0]
    assert saved['new-id']['name'] == 'A - copy'
    assert saved['new-id'] is not saved['a']
    assert saved['new-id']['config'] is not saved['a']['config']


def test_plugin_presets_update_name_only_changes_existing_preset():
    ctrl, window = _presets({'a': {'name': 'A'}})
    ctrl.update_name('a', 'Renamed')
    assert ctrl.store.call_args.args[0]['a']['name'] == 'Renamed'
    window.ui.dialog['rename'].close.assert_called_once_with()


def test_plugin_presets_store_delegates_to_core_storage():
    window = MagicMock()
    ctrl = Presets(window)
    data = {'x': {'name': 'X'}}
    ctrl.store(data)
    window.core.plugins.replace_presets.assert_called_once_with(data)
    window.core.plugins.save_presets.assert_called_once_with()


def test_plugin_presets_open_close_and_toggle_are_idempotent():
    window = MagicMock()
    ctrl = Presets(window)
    ctrl.setup = MagicMock()
    ctrl.open()
    ctrl.open()
    ctrl.setup.assert_called_once_with()
    window.ui.dialogs.open.assert_called_once()
    ctrl.close()
    window.ui.dialogs.close.assert_called_once_with('preset.plugins.editor')


def test_plugin_presets_remaining_index_routes_and_toggle_editor():
    ctrl, window = _presets({'a': {'name': 'A'}})
    ctrl.rename = MagicMock()
    ctrl.toggle = MagicMock()
    ctrl.duplicate = MagicMock()
    ctrl.get_id_by_idx = MagicMock(return_value='a')
    ctrl.rename_by_idx(0)
    ctrl.rename.assert_called_once_with('a')
    ctrl.select_by_idx(0)
    ctrl.toggle.assert_called_once_with('a')
    ctrl.duplicate_by_idx(0)
    ctrl.duplicate.assert_called_once_with('a')

    ctrl.dialog = False
    ctrl.open = MagicMock()
    ctrl.toggle_editor()
    ctrl.open.assert_called_once_with()
    ctrl.dialog = True
    ctrl.close = MagicMock()
    ctrl.toggle_editor()
    ctrl.close.assert_called_once_with()


def test_plugin_presets_reset_and_reset_by_idx():
    ctrl, window = _presets({'a': {'name': 'A', 'enabled': {'x': True}, 'config': {'x': 1}}})
    ctrl.get_current_id = MagicMock(return_value='a')
    ctrl.toggle = MagicMock()
    ctrl.reset('a')
    saved = ctrl.store.call_args.args[0]
    assert saved['a']['enabled'] == {}
    assert saved['a']['config'] == {}
    ctrl.toggle.assert_called_once_with('a')

    ctrl.reset = MagicMock()
    ctrl.get_id_by_idx = MagicMock(return_value='a')
    ctrl.reset_by_idx(0, False)
    window.ui.dialogs.confirm.assert_called_once()
    ctrl.reset_by_idx(0, True)
    ctrl.reset.assert_called_once_with('a')


def test_plugin_presets_getters_sort_by_name_and_recover_sort_error():
    window = MagicMock()
    ctrl = Presets(window)
    window.core.plugins.get_presets.return_value = {
        'z': {'name': 'Zulu'}, 'a': {'name': 'Alpha'}
    }
    assert list(ctrl.get_presets()) == ['a', 'z']
    assert ctrl.get_preset('z')['name'] == 'Zulu'
    assert ctrl.get_preset('missing') is None

    window.core.plugins.get_presets.return_value = {'bad': None}
    assert ctrl.get_presets() == {'bad': None}
    window.core.debug.error.assert_called_once()


def test_plugin_presets_update_marks_only_current_action():
    window = MagicMock()
    ctrl = Presets(window)
    a1, a2 = MagicMock(), MagicMock()
    window.ui.menu = {'plugins_presets': {'a': a1, 'b': a2}}
    window.core.config.get.return_value = 'b'
    ctrl.update()
    a1.setChecked.assert_called_with(False)
    a2.setChecked.assert_any_call(False)
    a2.setChecked.assert_called_with(True)


def test_plugin_presets_current_id_save_current_and_snapshot_roundtrip():
    ctrl, window = _presets({'a': {'name': 'A', 'enabled': {}, 'config': {}}})
    window.core.config.get.side_effect = lambda key: {
        'preset.plugins': 'a',
        'plugins_enabled': {'p': True},
        'plugins': {'p': {'x': 1}},
    }.get(key)
    assert ctrl.get_current_id() == 'a'
    ctrl.current_to_preset = MagicMock()
    ctrl.save_current()
    ctrl.current_to_preset.assert_called_once_with('a')

    ctrl.current_to_preset = Presets.current_to_preset.__get__(ctrl, Presets)
    ctrl.current_to_preset('a')
    saved = ctrl.store.call_args.args[0]
    assert saved['a']['enabled'] == {'p': True}
    assert saved['a']['config'] == {'p': {'x': 1}}


def test_plugin_presets_preset_to_current_deepcopies_and_reloads_open_settings():
    ctrl, window = _presets({'a': {
        'name': 'A', 'enabled': {'p': True}, 'config': {'p': {'x': [1]}}
    }})
    window.core.config.get.return_value = 'a'
    window.controller.plugins.settings.config_dialog = True
    ctrl.preset_to_current()
    window.core.config.set.assert_any_call('plugins_enabled', {'p': True})
    window.core.config.set.assert_any_call('plugins', {'p': {'x': [1]}})
    window.core.plugins.apply_all_options.assert_called_once_with()
    window.controller.plugins.settings.init.assert_called_once_with()
