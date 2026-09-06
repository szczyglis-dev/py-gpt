from pathlib import Path
from unittest.mock import MagicMock, patch

from pygpt_net.controller.settings.profile import Profile
from pygpt_net.core.types import MODE_CHAT


def _profile(data=None, current='p1'):
    window = MagicMock()
    window.ui.menu = {'config.profiles': {}, 'config.profile': MagicMock()}
    window.ui.nodes = {
        'dialog.profile.checkbox.switch': MagicMock(),
        'dialog.profile.checkbox.db': MagicMock(),
        'dialog.profile.checkbox.data': MagicMock(),
        'profile.list': MagicMock(),
    }
    window.ui.dialog = {'profile.item': MagicMock()}
    window.ui.models = {'profile.list': MagicMock()}
    window.core.config.profile.get_all.return_value = data or {
        'p1': {'name': 'One', 'workdir': '/tmp/one'},
        'p2': {'name': 'Two', 'workdir': '/tmp/two'},
    }
    window.core.config.profile.get_current.return_value = current
    return Profile(window), window


def test_profile_setup_builds_menu_and_dialog_once():
    ctrl, window = _profile()
    ctrl.setup_menu = MagicMock()
    ctrl.setup()
    ctrl.setup()
    assert ctrl.setup_menu.call_count == 2
    window.profiles.setup.assert_called_once_with()


def test_profile_switch_skips_current_unless_forced_and_alerts_missing():
    ctrl, window = _profile(current='p1')
    ctrl.update_menu = MagicMock()
    ctrl.switch('p1')
    ctrl.update_menu.assert_called_once_with()
    window.core.config.profile.set_current.assert_not_called()

    window.core.config.profile.get.return_value = None
    ctrl.switch('missing', force=True)
    window.ui.dialogs.alert.assert_called_once_with('Profile not found!')


def test_profile_switch_uses_existing_workdir_or_after_update():
    ctrl, window = _profile(current='p0')
    window.core.config.profile.get.return_value = {'name': 'Two'}
    window.core.config.profile.get_current_workdir.return_value = '/work/two'
    with patch('pygpt_net.controller.settings.profile.os.path.exists', return_value=True):
        ctrl.switch('p2', force=True, save_current=True, is_create=True)
    window.controller.settings.save_all.assert_called_once_with(force=True)
    window.core.config.profile.set_current.assert_called_once_with('p2')
    window.controller.settings.workdir.update.assert_called_once_with(
        '/work/two', force=True, profile_name='Two', is_create=True
    )

    ctrl.after_update = MagicMock()
    window.core.config.profile.get_current_workdir.return_value = '/missing'
    with patch('pygpt_net.controller.settings.profile.os.path.exists', return_value=False):
        ctrl.switch('p2', force=True, save_current=False)
    ctrl.after_update.assert_called_once_with('Two')


def test_profile_after_update_refreshes_ui_and_selection():
    ctrl, window = _profile()
    ctrl.update_menu = MagicMock()
    ctrl.update_list = MagicMock()
    ctrl.select_current_on_list = MagicMock()
    with patch('pygpt_net.controller.settings.profile.trans', return_value='Changed'):
        ctrl.after_update('Profile')
    ctrl.update_menu.assert_called_once_with()
    ctrl.update_list.assert_called_once_with()
    window.ui.update_title.assert_called_once_with()
    window.update_status.assert_called_once_with('Changed: Profile')
    window.ui.dialogs.close.assert_called_once_with('profile.item')
    ctrl.select_current_on_list.assert_called_once_with()


def test_profile_new_and_edit_populate_dialog_without_real_qt():
    ctrl, window = _profile()
    dialog = window.ui.dialog['profile.item']
    ctrl.new()
    assert dialog.mode == 'create'
    assert dialog.uuid is None
    dialog.prepare.assert_called()
    dialog.show.assert_called()

    window.core.config.profile.get.return_value = {'name': 'Name', 'workdir': '%HOME%/work'}
    ctrl.edit('p1')
    assert dialog.mode == 'edit'
    assert dialog.uuid == 'p1'
    dialog.input.setText.assert_called_with('Name')
    assert str(Path.home()) in dialog.path


def test_profile_open_close_toggle_are_idempotent():
    ctrl, window = _profile()
    ctrl.setup = MagicMock()
    ctrl.update_menu = MagicMock()
    ctrl.update_list = MagicMock()
    ctrl.select_current_on_list = MagicMock()
    ctrl.open()
    ctrl.open()
    ctrl.setup.assert_called_once_with()
    window.ui.dialogs.open.assert_called_once_with('profile.editor', width=500, height=500)
    ctrl.toggle_editor()
    window.ui.dialogs.close.assert_called_once_with('profile.editor')


def test_profile_handle_update_rejects_blank_fields_before_filesystem_access():
    ctrl, window = _profile()
    with patch('pygpt_net.controller.settings.profile.trans', side_effect=lambda key: key):
        ctrl.handle_update('create', '  ', '/tmp')
        ctrl.handle_update('create', 'Name', '   ')
    assert window.ui.dialogs.alert.call_count == 2
    window.core.filesystem.is_directory_empty.assert_not_called()


def test_profile_handle_update_create_with_real_temp_directory(tmp_path):
    ctrl, window = _profile()
    window.core.filesystem.is_directory_empty.return_value = True
    window.core.config.profile.add.return_value = 'new-id'
    window.ui.nodes['dialog.profile.checkbox.switch'].isChecked.return_value = False
    ctrl.update_menu = MagicMock()
    ctrl.update_list = MagicMock()

    ctrl.handle_update('create', '  Name  ', f'  {tmp_path}  ')

    window.core.config.profile.add.assert_called_once_with('Name', str(tmp_path))
    window.ui.dialogs.close.assert_called_once_with('profile.item')
    ctrl.update_menu.assert_called_once_with()
    ctrl.update_list.assert_called_once_with()


def test_profile_delete_by_idx_protects_current_and_batch_skips_it():
    ctrl, window = _profile(current='p1')
    ctrl.get_id_by_idx = MagicMock(side_effect=lambda i: ['p1', 'p2'][i])
    ctrl.delete = MagicMock()

    ctrl.delete_by_idx(0, True)
    window.ui.dialogs.alert.assert_called_once()
    ctrl.delete.assert_not_called()

    ctrl.delete_by_idx([0, 1], True)
    ctrl.delete.assert_called_once_with(['p2'])


def test_profile_delete_reset_and_duplicate_delegate_to_workdir():
    ctrl, window = _profile()
    ctrl.delete_all(['p1', 'p2'])
    window.controller.settings.workdir.delete_files.assert_called_once_with(['p1', 'p2'], batch=True)

    ctrl.reset(['p1', 'p2'])
    window.controller.settings.workdir.reset.assert_called_once_with(['p1', 'p2'], batch=True)

    ctrl.duplicate('p1', 'Copy', '/tmp/copy')
    window.controller.settings.workdir.duplicate.assert_called_once_with(
        profile_uuid='p1', new_name='Copy', new_path='/tmp/copy'
    )


def test_profile_after_create_finish_selects_chat_mode():
    ctrl, window = _profile()
    ctrl.update_menu = MagicMock()
    ctrl.update_list = MagicMock()
    ctrl.after_create_finish('p2')
    window.controller.mode.select.assert_called_once_with(MODE_CHAT)


def test_profile_flags_indices_and_list_helpers():
    ctrl, window = _profile()
    window.ui.nodes['dialog.profile.checkbox.db'].isChecked.return_value = True
    window.ui.nodes['dialog.profile.checkbox.data'].isChecked.return_value = False
    assert ctrl.is_include_db() is True
    assert ctrl.is_include_datadir() is False
    assert ctrl.get_id_by_idx(0) == 'p1'
    assert ctrl.get_id_by_idx(99) is None
    ctrl.update_list()
    window.profiles.update_list.assert_called_once()


def test_profile_remaining_index_and_callback_helpers_delegate_cleanly():
    ctrl, window = _profile()
    ctrl.switch = MagicMock()
    ctrl.switch_current('p2')
    ctrl.switch.assert_called_once_with('p2', force=True, save_current=False)

    ctrl.edit = MagicMock()
    ctrl.get_id_by_idx = MagicMock(return_value='p2')
    ctrl.edit_by_idx(1)
    ctrl.edit.assert_called_once_with('p2')

    ctrl.switch.reset_mock()
    ctrl.select_by_idx(1)
    ctrl.switch.assert_called_once_with('p2')

    ctrl.update_menu = MagicMock()
    ctrl.update_list = MagicMock()
    ctrl.dismiss_update()
    window.ui.dialogs.close.assert_called_with('profile.item')

    with patch('pygpt_net.controller.settings.profile.trans', return_value='Deleted'):
        ctrl.after_delete('Two')
    window.update_status.assert_called_with('Deleted: Two')


def test_profile_after_create_and_duplicate_switch_paths():
    ctrl, window = _profile()
    ctrl.switch = MagicMock()
    window.core.config.get.side_effect = lambda key: {'theme': 'dark', 'lang': 'pl'}[key]
    ctrl.after_create('p2')
    assert ctrl.before_theme == 'dark'
    assert ctrl.before_language == 'pl'
    ctrl.switch.assert_called_once_with(
        'p2', force=True, on_finish=ctrl.after_create_finish, is_create=True
    )

    ctrl.update_menu = MagicMock()
    ctrl.update_list = MagicMock()
    ctrl.switch.reset_mock()
    window.ui.nodes['dialog.profile.checkbox.switch'].isChecked.return_value = True
    ctrl.after_duplicate('p3', 'Copy')
    ctrl.switch.assert_called_once_with('p3', force=True)


def test_profile_force_batch_confirm_helpers():
    ctrl, window = _profile()
    ctrl.get_id_by_idx = MagicMock(side_effect=lambda i: ['p1', 'p2'][i])
    ctrl.delete_all = MagicMock()
    ctrl.reset = MagicMock()

    ctrl.delete_all_by_idx(1, False)
    window.ui.dialogs.confirm.assert_called_once()
    ctrl.delete_all_by_idx(1, True)
    ctrl.delete_all.assert_called_once_with(['p2'])

    ctrl.reset_by_idx([0, 1], False)
    assert window.ui.dialogs.confirm.call_count == 2
    ctrl.reset_by_idx([0, 1], True)
    ctrl.reset.assert_called_once_with(['p1', 'p2'])


def test_profile_duplicate_by_idx_populates_copy_dialog():
    ctrl, window = _profile()
    ctrl.get_id_by_idx = MagicMock(return_value='p1')
    window.core.config.profile.get.return_value = {'name': 'One'}
    dialog = window.ui.dialog['profile.item']
    ctrl.duplicate_by_idx(0)
    assert dialog.mode == 'duplicate'
    assert dialog.uuid == 'p1'
    dialog.input.setText.assert_called_once_with('One - copy')
    dialog.show.assert_called_once_with()


def test_profile_get_profiles_delegates_to_profile_config():
    ctrl, window = _profile()
    result = ctrl.get_profiles()
    assert result == window.core.config.profile.get_all.return_value
    window.core.config.profile.get_all.assert_called_once_with()
