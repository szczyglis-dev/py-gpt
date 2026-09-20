from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.remote_store.batch import Batch


def _batch(provider='openai'):
    ctrl = MagicMock()
    ctrl.window = MagicMock()
    ctrl.provider_key = provider
    ctrl.current = 'store-1'
    return Batch(ctrl), ctrl, ctrl.window


def test_remote_batch_confirmation_then_forced_store_import_uses_mocked_importer():
    batch, ctrl, window = _batch()
    importer = MagicMock()
    batch._importer = MagicMock(return_value=importer)

    batch.import_stores(False)
    window.ui.dialogs.confirm.assert_called_once()
    importer.import_vector_stores.assert_not_called()

    batch.import_stores(True)
    ctrl._core_for.return_value.truncate.assert_called_once_with()
    importer.import_vector_stores.assert_called_once_with()


def test_remote_batch_store_file_operations_support_single_and_multiple_ids():
    batch, _, window = _batch()
    importer = MagicMock()
    batch._importer = MagicMock(return_value=importer)

    batch.import_store_files(None, True)
    window.ui.dialogs.alert.assert_called_once()
    importer.import_files.assert_not_called()

    batch.import_store_files('s1', True)
    importer.import_files.assert_called_once_with('s1')

    batch.truncate_store_files(['s1', 's2'], True)
    assert importer.truncate_files.call_args_list[-2:] == [
        (( 's1',), {}), (( 's2',), {})
    ]


def test_remote_batch_clear_files_uses_provider_specific_local_store_without_external_api():
    batch, ctrl, window = _batch('google')
    files_core = MagicMock()
    ctrl._files_core_for.return_value = files_core
    with patch('pygpt_net.controller.remote_store.batch.QApplication.processEvents'):
        batch.clear_store_files(['a', 'b'], True)
    assert files_core.truncate_local.call_count == 2
    ctrl._files_core_for.assert_called_with('google')
    ctrl.update.assert_called_once_with()
    window.ui.dialogs.alert.assert_called_once()


def test_remote_batch_upload_resets_queue_and_calls_importer():
    batch, ctrl, _ = _batch()
    importer = MagicMock()
    batch._importer = MagicMock(return_value=importer)
    batch.files_to_upload = ['/tmp/a', '/tmp/b']
    with patch('pygpt_net.controller.remote_store.batch.QApplication.processEvents'):
        batch.upload(True)
    importer.upload_files.assert_called_once_with('store-1', ['/tmp/a', '/tmp/b'])
    assert batch.files_to_upload == []


def test_remote_batch_upload_rejects_missing_current_store():
    batch, ctrl, window = _batch()
    ctrl.current = None
    batch.upload(True)
    window.ui.dialogs.alert.assert_called_once()


def test_remote_batch_open_upload_files_mocks_native_file_dialog():
    batch, _, window = _batch()
    with patch('pygpt_net.controller.remote_store.batch.QFileDialog.Options', return_value=object()), \
         patch('pygpt_net.controller.remote_store.batch.QFileDialog.getOpenFileNames', return_value=(['a.txt', 'b.txt'], '')):
        batch.open_upload_files()
    assert batch.files_to_upload == ['a.txt', 'b.txt']
    window.ui.dialogs.confirm.assert_called_once()


def test_remote_batch_refresh_delayed_mocks_qtimer_and_executes_callback():
    batch, ctrl, window = _batch()
    with patch('pygpt_net.controller.remote_store.batch.QTimer.singleShot', side_effect=lambda ms, fn: fn()) as timer:
        batch.refresh_delayed(25)
        ctrl.refresh_status.assert_called_once_with()
        batch.refresh_delayed(30, all=True)
    assert timer.call_count == 2


def test_remote_batch_signal_handlers_update_state_and_report_errors():
    batch, ctrl, window = _batch()
    batch._get_provider = MagicMock(return_value='openai')
    batch.handle_imported_stores(3)
    ctrl.after_imported_stores.assert_called_once_with('openai')
    ctrl.update.assert_called()
    window.update_status.assert_called_with('OK. Imported stores: 3.')

    error = RuntimeError('remote failed')
    batch.handle_imported_files_failed(error)
    window.core.debug.log.assert_called_with(error)
    window.ui.dialogs.alert.assert_called_with(error)


def test_remote_batch_importer_is_resolved_from_selected_provider():
    batch, _, window = _batch('google')
    importer = MagicMock()
    window.core.api.google.store.importer = importer
    assert batch._importer() is importer


def test_remote_batch_remaining_store_starters_use_mocked_qt_and_importer():
    batch, _, window = _batch()
    importer = MagicMock()
    batch._importer = MagicMock(return_value=importer)
    with patch('pygpt_net.controller.remote_store.batch.QApplication.processEvents'):
        batch.truncate_stores(True)
        batch.refresh_stores(True)
        batch.truncate_files(True)
    importer.truncate_vector_stores.assert_called_once_with()
    importer.refresh_vector_stores.assert_called_once_with()
    importer.truncate_files.assert_called_once_with()


def test_remote_batch_assistant_file_import_guards_and_forced_routes():
    batch, _, window = _batch()
    window.core.config.get.return_value = ''
    batch.import_files_assistant_current(True)
    window.core.api.openai.store.importer.import_files.assert_not_called()

    window.core.config.get.return_value = 'a1'
    window.core.assistants.has.return_value = True
    window.core.assistants.get_by_id.return_value = SimpleNamespace(vector_store='s1')
    batch.import_files_assistant_current(True)
    window.core.api.openai.store.importer.import_files.assert_called_once_with('s1')

    batch.import_files_assistant_all(True)
    window.core.api.openai.store.importer.import_files.assert_called_with()


def test_remote_batch_clear_stores_and_all_files_use_provider_core():
    batch, ctrl, window = _batch('openai')
    store_core, files_core = MagicMock(), MagicMock()
    ctrl._core_for.return_value = store_core
    ctrl._files_core_for.return_value = files_core
    with patch('pygpt_net.controller.remote_store.batch.QApplication.processEvents'):
        batch.clear_stores(True)
        batch.clear_files(True)
    store_core.truncate.assert_called_once_with()
    files_core.truncate_local.assert_called_once_with()
    ctrl.update.assert_called()
    window.controller.assistant.files.update.assert_called_once_with()


def test_remote_batch_open_upload_dir_mocks_native_dialog_and_filesystem_scan():
    batch, _, window = _batch()
    window.core.filesystem.get_files_from_dir.return_value = ['/dir/a', '/dir/b']
    with patch('pygpt_net.controller.remote_store.batch.QFileDialog.Options', return_value=object()), \
         patch('pygpt_net.controller.remote_store.batch.QFileDialog.getExistingDirectory', return_value='/dir'):
        batch.open_upload_dir()
    assert batch.files_to_upload == ['/dir/a', '/dir/b']
    window.ui.dialogs.confirm.assert_called_once()


def test_remote_batch_remaining_success_handlers_update_expected_state():
    batch, ctrl, window = _batch()
    batch.refresh_delayed = MagicMock()
    batch._get_provider = MagicMock(return_value='openai')

    batch.handle_refreshed_stores(2)
    ctrl.update.assert_called()
    window.ui.dialogs.alert.assert_called()

    batch.handle_truncated_stores(2)
    ctrl._core_for.return_value.truncate.assert_called_once_with()
    ctrl.after_truncated_stores.assert_called_once_with('openai')
    assert ctrl.current is None
    ctrl.init.assert_called()

    batch.handle_imported_files(4)
    window.controller.assistant.files.update.assert_called()
    batch.handle_truncated_files('s1', 3)
    ctrl.refresh_by_store_id_provider.assert_called_once_with('openai', 's1')
    batch.handle_uploaded_files(5)
    batch.refresh_delayed.assert_called_with(1500)


def test_remote_batch_all_failure_handlers_log_alert_and_keep_ui_responsive():
    batch, ctrl, window = _batch()
    batch.refresh_delayed = MagicMock()
    error = RuntimeError('failed')
    batch.handle_refreshed_stores_failed(error)
    batch.handle_imported_stores_failed(error)
    batch.handle_truncated_stores_failed(error)
    batch.handle_truncated_files_failed(error)
    batch.handle_uploaded_files_failed(error)
    assert window.core.debug.log.call_count == 5
    assert window.ui.dialogs.alert.call_count == 5
    ctrl.update.assert_called()
    batch.refresh_delayed.assert_called_with(1500)
