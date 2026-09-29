from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.remote_store.remote_store import RemoteStore


def _store():
    window = MagicMock()
    ctrl = RemoteStore(window)
    return ctrl, window


def test_remote_store_provider_helpers_fallback_and_persist_default():
    ctrl, window = _store()
    window.core.config.get.return_value = 'invalid'
    assert ctrl.get_provider_keys() == ['openai', 'google', 'xai']
    assert ctrl._get_provider() == 'openai'
    window.core.config.set.assert_called_once_with('remote_store.provider', 'openai')


def test_remote_store_set_provider_rejects_unknown_and_reinitializes_known():
    ctrl, window = _store()
    ctrl.init = MagicMock()
    ctrl.set_provider('bad')
    ctrl.init.assert_not_called()
    ctrl.set_provider('google')
    assert ctrl.provider_key == 'google'
    window.core.config.set.assert_called_once_with('remote_store.provider', 'google')
    ctrl.init.assert_called_once_with(select_first=True)


def test_remote_store_resolves_provider_core_files_and_api_store():
    ctrl, window = _store()
    core = MagicMock()
    window.core.remote_store.openai = core
    api_store = MagicMock()
    window.core.api.openai.store = api_store
    assert ctrl._core_for('openai') is core
    assert ctrl._files_core_for('openai') is core.files
    assert ctrl._api_store_for('openai') is api_store


def test_remote_store_openai_hooks_update_assistant_views_only_for_openai():
    ctrl, window = _store()
    ctrl.after_create('google', SimpleNamespace())
    window.controller.assistant.editor.update_store_list.assert_not_called()
    ctrl.after_create('openai', SimpleNamespace())
    window.controller.assistant.editor.update_store_list.assert_called_once_with()
    ctrl.after_delete('openai', 's1')
    ctrl.after_update('openai')
    assert window.controller.assistant.editor.update_store_list.call_count == 3


def test_remote_store_setup_and_reload_catch_provider_loading_errors():
    ctrl, window = _store()
    window.core.remote_store.openai.load_all.side_effect = RuntimeError('load failed')
    ctrl.setup()
    window.core.debug.log.assert_called_once()
    ctrl.reset = MagicMock()
    ctrl.reload()
    assert window.core.debug.log.call_count == 2
    ctrl.reset.assert_called_once_with()


def test_remote_store_open_close_and_reset_lifecycle():
    ctrl, window = _store()
    ctrl.setup = MagicMock()
    ctrl.init = MagicMock()
    ctrl.open()
    ctrl.open()
    ctrl.setup.assert_called_once_with()
    ctrl.init.assert_called_once_with(select_first=True)
    window.ui.dialogs.open.assert_called_once_with('remote_store', width=900, height=560)
    ctrl.close()
    window.ui.dialogs.close.assert_called_once_with('remote_store')
    ctrl.dialog = True
    ctrl.current = 'x'
    ctrl.reset()
    assert ctrl.current is None
    assert ctrl.init.call_count == 2


def test_remote_store_row_mapping_helpers_have_safe_bounds_and_fallback():
    ctrl, _ = _store()
    ctrl._stores_row_to_id = ['a', 'b']
    assert ctrl.get_tab_idx('b') == 1
    assert ctrl.get_tab_idx('missing') is None
    assert ctrl.get_tab_by_id('a') == 0
    assert ctrl.get_by_tab_idx(-1) is None
    assert ctrl.get_by_tab_idx(0) == 'a'
    assert ctrl.get_by_tab_idx(2) is None
    assert ctrl.get_first_visible() == 'a'


def test_remote_store_get_first_visible_falls_back_to_core_and_skips_hidden():
    ctrl, _ = _store()
    ctrl._stores_row_to_id = []
    core = MagicMock()
    core.get_ids.return_value = ['hidden', 'visible']
    core.is_hidden.side_effect = lambda sid: sid == 'hidden'
    ctrl._core_for = MagicMock(return_value=core)
    assert ctrl.get_first_visible() == 'visible'


def test_remote_store_select_saves_current_then_refreshes_selected_files():
    ctrl, _ = _store()
    ctrl.save = MagicMock()
    ctrl.init = MagicMock()
    ctrl.update_files_list = MagicMock()
    ctrl._stores_row_to_id = ['s1']
    ctrl.select(0)
    ctrl.save.assert_called_once_with(persist=False)
    assert ctrl.current == 's1'
    ctrl.init.assert_called_once_with()
    ctrl.update_files_list.assert_called_once_with()


def test_remote_store_hide_threads_config_is_provider_agnostic_and_updates():
    ctrl, window = _store()
    ctrl.provider_key = 'xai'
    ctrl.update = MagicMock()
    ctrl.set_hide_thread(True)
    window.core.config.set.assert_called_once_with('remote_store.hide_threads', True)
    ctrl.update.assert_called_once_with()
    window.core.config.get.return_value = False
    assert ctrl._get_hide_threads_config('google') is False


def test_remote_store_batch_entrypoints_confirm_then_use_mocked_importer():
    ctrl, window = _store()
    ctrl.provider_key = 'openai'
    importer = MagicMock()
    core = MagicMock()
    ctrl._importer_for = MagicMock(return_value=importer)
    ctrl._core_for = MagicMock(return_value=core)

    ctrl.import_stores(False)
    window.ui.dialogs.confirm.assert_called_once()
    importer.import_vector_stores.assert_not_called()

    ctrl.import_stores(True)
    core.truncate.assert_called_once_with()
    importer.import_vector_stores.assert_called_once_with()

    ctrl.import_store_files('s1', True)
    importer.import_files.assert_called_once_with('s1')


def test_remote_store_clear_store_files_mocks_qt_and_handles_multiple_ids():
    ctrl, window = _store()
    ctrl.provider_key = 'openai'
    files = MagicMock()
    ctrl._files_core_for = MagicMock(return_value=files)
    ctrl.update = MagicMock()
    with patch('pygpt_net.controller.remote_store.remote_store.QApplication.processEvents'):
        ctrl.clear_store_files(['a', 'b'], True)
    assert files.truncate_local.call_count == 2
    ctrl.update.assert_called_once_with()
    window.ui.dialogs.alert.assert_called_once()


def test_remote_store_importer_for_returns_selected_external_importer():
    ctrl, window = _store()
    importer = MagicMock()
    window.core.api.xai.store.importer = importer
    assert ctrl._importer_for('xai') is importer


def test_remote_store_options_and_toggle_editor_helpers():
    ctrl, _ = _store()
    assert ctrl.get_providers() is ctrl.PROVIDERS
    assert ctrl.get_options() is ctrl.options
    assert ctrl.get_option('name') is ctrl.options['name']
    assert ctrl.get_option('missing') is None
    ctrl.set_provider = MagicMock()
    ctrl.open = MagicMock()
    ctrl.toggle_editor('google')
    ctrl.set_provider.assert_called_once_with('google')
    ctrl.open.assert_called_once_with()


def test_remote_store_after_truncate_openai_cleans_assistant_links():
    ctrl, window = _store()
    ctrl.after_truncated_stores('openai')
    window.controller.assistant.batch.remove_all_stores_from_assistants.assert_called_once_with()
    window.controller.assistant.editor.update_store_list.assert_called_once_with()


def test_remote_store_refresh_store_and_index_routes_use_mocked_provider_core():
    ctrl, _ = _store()
    ctrl.provider_key = 'openai'
    store = SimpleNamespace(id='s1')
    core = MagicMock()
    core.has.return_value = True
    core.items = {'s1': store, 's2': SimpleNamespace(id='s2')}
    ctrl._core_for = MagicMock(return_value=core)
    ctrl.update_current = MagicMock()
    ctrl.current = 's1'
    ctrl.refresh_store(store)
    core.update_status.assert_called_with('s1')
    core.update.assert_called_with(store)
    ctrl.update_current.assert_called_once_with()

    ctrl.get_by_tab_idx = MagicMock(side_effect=lambda i: ['s1', 's2'][i] if i in (0, 1) else None)
    ctrl.refresh_by_store_id = MagicMock()
    ctrl.refresh_by_idx([0, 1, 9])
    ctrl.refresh_by_store_id.assert_called_once_with(['s1', 's2'])


def test_remote_store_refresh_by_store_id_provider_ignores_missing_and_updates_current():
    ctrl, _ = _store()
    ctrl.provider_key = 'openai'
    store = SimpleNamespace(id='s1')
    core = MagicMock(items={'s1': store})
    ctrl._core_for = MagicMock(return_value=core)
    ctrl.current = 's1'
    ctrl.update_current = MagicMock()
    ctrl.update = MagicMock()
    ctrl.update_files_list = MagicMock()
    ctrl.refresh_by_store_id_provider('openai', 's1')
    core.update_status.assert_called_once_with('s1')
    core.update.assert_called_once_with(store)
    ctrl.update_current.assert_called_once_with()
    ctrl.update.assert_called_once_with()
    ctrl.update_files_list.assert_called_once_with()


def test_remote_store_update_current_applies_store_fields_without_real_widgets():
    ctrl, window = _store()
    ctrl.provider_key = 'openai'
    store = SimpleNamespace(id='s1', name='Store', status={'ok': True}, expire_days=7)
    core = MagicMock()
    core.has.return_value = True
    core.items = {'s1': store}
    ctrl._core_for = MagicMock(return_value=core)
    ctrl.current = 's1'
    ctrl.update_current()
    keys = [c.args[1] for c in window.controller.config.apply.call_args_list]
    assert keys == ['status', 'name', 'id', 'expire_days']


def test_remote_store_reload_items_filters_hidden_and_thread_entries():
    ctrl, window = _store()
    ctrl.provider_key = 'openai'
    visible = SimpleNamespace(id='v', name='Visible', usage_bytes=0, get_file_count=lambda: 2)
    hidden = SimpleNamespace(id='h', name='Hidden', usage_bytes=0, get_file_count=lambda: 0)
    unnamed = SimpleNamespace(id='u', name='', usage_bytes=0, get_file_count=lambda: 0)
    core = MagicMock()
    core.get_all.return_value = {'v': visible, 'h': hidden, 'u': unnamed}
    core.is_hidden.side_effect = lambda sid: sid == 'h'
    ctrl._core_for = MagicMock(return_value=core)
    ctrl._get_hide_threads_config = MagicMock(return_value=True)
    ctrl.restore_selection = MagicMock()
    with patch('pygpt_net.controller.remote_store.remote_store.trans', return_value='files'):
        ctrl.reload_items()
    assert ctrl._stores_row_to_id == ['v']
    window.remote_store.update_list_pairs.assert_called_once_with(
        'remote_store.list', [('v', 'Visible (2 files)')]
    )
    ctrl.restore_selection.assert_called_once_with()


def test_remote_store_selection_helpers_delegate_to_ui():
    ctrl, window = _store()
    ctrl._stores_row_to_id = ['a', 'b']
    ctrl.set_by_tab(1)
    window.remote_store.set_current_row.assert_called_once_with('remote_store.list', 1)
    ctrl.set_by_tab = MagicMock()
    ctrl.set_tab_by_id('b')
    ctrl.set_by_tab.assert_called_once_with(1)
    ctrl.current = 'a'
    ctrl.restore_selection()
    ctrl.set_by_tab.assert_called_with(0)


def test_remote_store_save_btn_and_new_dialog_helpers():
    ctrl, window = _store()
    ctrl.save = MagicMock()
    ctrl.refresh_status = MagicMock()
    ctrl.save_btn()
    ctrl.save.assert_called_once_with()
    ctrl.refresh_status.assert_called_once_with()
    assert window.update_status.call_args_list[-1].args == ('Saved.',)

    ctrl.new('Name', False)
    dialog = window.ui.dialog['create']
    assert dialog.id == 'remote_store.new'
    dialog.show.assert_called_once_with()


def test_remote_store_delete_by_idx_and_delete_confirmation():
    ctrl, window = _store()
    ctrl._stores_row_to_id = ['a', 'b']
    ctrl.delete = MagicMock()
    ctrl.delete_by_idx([0, 9, 1], True)
    ctrl.delete.assert_called_once_with(['a', 'b'], True)

    ctrl.delete = RemoteStore.delete.__get__(ctrl, RemoteStore)
    ctrl.delete('a', False)
    window.ui.dialogs.confirm.assert_called_once()


def test_remote_store_update_files_list_mocks_qstandarditem():
    ctrl, window = _store()
    model = MagicMock()
    model.rowCount.return_value = 0
    window.ui.models = {'remote_store.files.list': model}
    ctrl.current = 's1'
    files = MagicMock()
    files.get_by_store_or_thread.return_value = {
        'f1': {'file_id': 'remote-f1', 'name': 'file.txt', 'size': 1024, 'status': 'ready'}
    }
    ctrl._files_core_for = MagicMock(return_value=files)
    window.core.filesystem.sizeof_fmt.return_value = '1 KB'
    item = MagicMock()
    with patch('pygpt_net.controller.remote_store.remote_store.QStandardItem', return_value=item) as factory:
        ctrl.update_files_list()
    factory.assert_called_once_with('file.txt (1 KB, ready)')
    item.setEditable.assert_called_once_with(False)
    model.setItem.assert_called_once_with(0, 0, item)
    assert ctrl._files_row_to_id == ['remote-f1']


def test_remote_store_delete_file_by_idx_guards_and_provider_call():
    ctrl, window = _store()
    window.ui.models = {'remote_store.files.list': MagicMock()}
    ctrl.current = 's1'
    ctrl._files_row_to_id = ['f1']
    ctrl.provider_key = 'openai'
    ctrl._delete_file_by_idx_provider = MagicMock()
    ctrl.delete_file_by_idx([], True)
    ctrl._delete_file_by_idx_provider.assert_not_called()
    ctrl.delete_file_by_idx(0, True)
    ctrl._delete_file_by_idx_provider.assert_called_once_with([0], 'openai')


def test_remote_store_remaining_batch_entrypoints_use_mocked_importer():
    ctrl, _ = _store()
    ctrl.provider_key = 'openai'
    importer, core = MagicMock(), MagicMock()
    ctrl._importer_for = MagicMock(return_value=importer)
    ctrl._core_for = MagicMock(return_value=core)
    ctrl.refresh_stores(True)
    ctrl.truncate_stores(True)
    ctrl.truncate_files(True)
    importer.refresh_vector_stores.assert_called_once_with()
    importer.truncate_vector_stores.assert_called_once_with()
    importer.truncate_files.assert_called_once_with()
    core.truncate.assert_called_once_with()


def test_remote_store_clear_all_files_and_stores_mock_qt_processing():
    ctrl, window = _store()
    ctrl.provider_key = 'openai'
    files, core = MagicMock(), MagicMock()
    ctrl._files_core_for = MagicMock(return_value=files)
    ctrl._core_for = MagicMock(return_value=core)
    ctrl.update = MagicMock()
    ctrl.init = MagicMock()
    with patch('pygpt_net.controller.remote_store.remote_store.QApplication.processEvents'):
        ctrl.clear_files(True)
        ctrl.clear_stores(True)
    files.truncate_local.assert_called_once_with()
    core.truncate.assert_called_once_with()
    ctrl.update.assert_called()
    ctrl.init.assert_called_once_with()
