from unittest.mock import MagicMock, mock_open, patch

from pygpt_net.controller.settings.workdir import Workdir, WorkdirWorker


def _workdir():
    window = MagicMock()
    ctrl = Workdir(window)
    return ctrl, window


def test_workdir_update_workdir_writes_portable_home_placeholder_and_preserves_create_theme():
    ctrl, window = _workdir()
    window.core.config.get_base_workdir.return_value = '/base'
    window.core.config.get.side_effect = lambda key: {'theme': 'dark', 'lang': 'pl'}.get(key)
    m = mock_open()
    with patch('pygpt_net.controller.settings.workdir.open', m), \
         patch('pygpt_net.controller.settings.workdir.Path.home', return_value='/home/test'):
        ctrl.update_workdir(True, '/home/test/new', is_create=True)
    m.assert_called_once_with('/base/path.cfg', 'w', encoding='utf-8')
    m().write.assert_called_once_with('%HOME%/new')
    window.core.config.profile.update_current_workdir.assert_called_once_with('/home/test/new')
    window.core.config.set_workdir.assert_called_once_with('/home/test/new', reload=True)
    window.core.config.set.assert_any_call('theme', 'dark')
    window.core.config.set.assert_any_call('lang', 'pl')
    window.core.config.set.assert_any_call('license.accepted', True)


def test_workdir_rollback_writes_empty_lock_for_default_and_reloads():
    ctrl, window = _workdir()
    window.core.config.get_base_workdir.return_value = '/base'
    m = mock_open()
    with patch('pygpt_net.controller.settings.workdir.open', m):
        ctrl.rollback('/base')
    m().write.assert_called_once_with('')
    window.core.config.set_workdir.assert_called_once_with('/base', reload=True)
    window.controller.reload.assert_called_once_with()
    window.core.config.profile.update_current_workdir.assert_called_once_with('/base')


def test_workdir_do_update_success_and_failure_paths():
    ctrl, window = _workdir()
    ctrl.update_workdir = MagicMock()
    ctrl.rollback = MagicMock()
    assert ctrl.do_update(False, 'Name', '/old', '/new') is False
    window.controller.reload.assert_called_once_with()
    window.controller.settings.profile.after_update.assert_called_once_with('Name')

    window.controller.reload.reset_mock()
    window.controller.reload.side_effect = RuntimeError('reload failed')
    assert ctrl.do_update(True, 'Name', '/old', '/new') is False
    ctrl.rollback.assert_called_once_with(current='/old')
    window.core.debug.log.assert_called()


def test_workdir_do_update_force_success_returns_true():
    ctrl, window = _workdir()
    ctrl.update_workdir = MagicMock()
    assert ctrl.do_update(True, 'Name', '/old', '/new') is True
    window.controller.settings.profile.after_update.assert_called_once_with('Name')
    window.ui.dialogs.alert.assert_called()


def test_workdir_do_migrate_success_clears_old_directory_and_unlocks():
    ctrl, window = _workdir()
    ctrl.do_update = MagicMock(return_value=True)
    assert ctrl.do_migrate(True, 'Name', '/old', '/new') is True
    window.core.filesystem.clear_workdir.assert_called_once_with('/old')
    assert window.controller.settings.workdir.busy is False


def test_workdir_change_toggles_dialog():
    ctrl, window = _workdir()
    window.core.config.get_user_path.return_value = '/work'
    ctrl.change()
    window.ui.dialogs.open.assert_called_once_with('workdir.change', width=600, height=180)
    assert ctrl.is_dialog is True
    ctrl.change()
    window.ui.dialogs.close.assert_called_once_with('workdir.change')
    assert ctrl.is_dialog is False


def test_workdir_run_action_uses_external_worker_mock_and_threadpool():
    ctrl, window = _workdir()
    worker = MagicMock()
    worker.signals = MagicMock()
    with patch('pygpt_net.controller.settings.workdir.WorkdirWorker', return_value=worker) as factory:
        ctrl.run_action('reset', profile_uuid='p1', batch=True)
    factory.assert_called_once()
    assert factory.call_args.kwargs['action'] == 'reset'
    assert factory.call_args.kwargs['profile_uuid'] == 'p1'
    window.threadpool.start.assert_called_once_with(worker)


def test_workdir_delegate_methods_build_expected_actions():
    ctrl, window = _workdir()
    ctrl.run_action = MagicMock()
    ctrl.do_update = MagicMock()
    window.core.config.get_user_path.return_value = '/old'
    ctrl.update('/new', force=True, profile_name='Name', is_create=True)
    ctrl.do_update.assert_called_once_with(
        force=True, profile_name='Name', current_path='/old', new_path='/new', is_create=True
    )
    ctrl.migrate('/m', True)
    ctrl.delete_files(['a', 'b'], batch=True)
    ctrl.duplicate('a', 'Copy', '/copy')
    ctrl.reset('a')
    assert ctrl.run_action.call_count == 4


def test_workdir_worker_run_routes_action_and_always_cleans_up():
    worker = WorkdirWorker.__new__(WorkdirWorker)
    worker.window = MagicMock()
    worker.action = 'duplicate'
    worker.signals = MagicMock()
    worker.worker_duplicate = MagicMock()
    worker.cleanup = MagicMock()
    worker.run()
    worker.worker_duplicate.assert_called_once_with()
    worker.signals.finished.emit.assert_called_once_with()
    worker.cleanup.assert_called_once_with()


def test_workdir_worker_unknown_action_emits_error():
    worker = WorkdirWorker.__new__(WorkdirWorker)
    worker.window = MagicMock()
    worker.action = 'unknown'
    worker.signals = MagicMock()
    worker.cleanup = MagicMock()
    worker.run()
    worker.signals.error.emit.assert_called_once_with('Unknown action: unknown')


def test_workdir_restore_is_alias_for_rollback():
    ctrl, _ = _workdir()
    ctrl.rollback = MagicMock()
    ctrl.restore('/current')
    ctrl.rollback.assert_called_once_with(current='/current')


def test_workdir_worker_delete_missing_path_uses_mocked_os_checks():
    worker = WorkdirWorker.__new__(WorkdirWorker)
    worker.window = MagicMock()
    worker.profile_uuid = 'p1'
    worker.batch = False
    worker.signals = MagicMock()
    worker.window.controller.settings.profile.get_profiles.return_value = {
        'p1': {'name': 'One', 'workdir': '/missing'}
    }
    worker.window.core.config.profile.remove.return_value = True
    with patch('pygpt_net.controller.settings.workdir.os.path.exists', return_value=False):
        worker.worker_delete_files()
    worker.signals.deleted.emit.assert_called_once_with('One')
    worker.signals.alert.emit.assert_called_once()
    worker.window.core.filesystem.clear_workdir.assert_not_called()


def test_workdir_worker_reset_current_profile_closes_db_and_switches():
    worker = WorkdirWorker.__new__(WorkdirWorker)
    worker.window = MagicMock()
    worker.profile_uuid = 'p1'
    worker.batch = False
    worker.signals = MagicMock()
    worker.window.controller.settings.profile.get_profiles.return_value = {
        'p1': {'name': 'One', 'workdir': '/work'}
    }
    worker.window.core.config.profile.get_current.return_value = 'p1'
    with patch('pygpt_net.controller.settings.workdir.os.path.exists', return_value=True), \
         patch('pygpt_net.controller.settings.workdir.os.path.isdir', return_value=True):
        worker.worker_reset()
    worker.window.core.db.close.assert_called_once_with()
    worker.window.core.filesystem.clear_workdir.assert_called_once_with(
        '/work', remove_db=True, remove_datadir=False
    )
    worker.signals.switch.emit.assert_called_once_with('p1')


def test_workdir_worker_migrate_same_directory_stops_before_copy():
    worker = WorkdirWorker.__new__(WorkdirWorker)
    worker.window = MagicMock()
    worker.path = '/same'
    worker.force = True
    worker.profile_name = 'P'
    worker.signals = MagicMock()
    worker.window.core.config.get_user_path.return_value = '/same'
    worker.worker_migrate()
    worker.signals.alert.emit.assert_called_once()
    worker.window.core.filesystem.copy_workdir.assert_not_called()
