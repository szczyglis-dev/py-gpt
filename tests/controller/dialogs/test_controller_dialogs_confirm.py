from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.dialogs.confirm import Confirm


def _ctrl():
    window = MagicMock()
    window.ui.dialog = {
        'confirm': MagicMock(), 'rename': MagicMock(), 'create': MagicMock(), 'url': MagicMock()
    }
    return Confirm(window), window


@pytest.mark.parametrize(
    ('kind', 'target', 'method', 'args', 'kwargs'),
    [
        ('ctx.delete', 'controller.ctx', 'delete', ('ctx-1', True), {}),
        ('preset_delete', 'controller.presets', 'delete', ('p-1', True), {}),
        ('attachments.delete', 'controller.attachment', 'delete', ('a-1',), {'force': True, 'remove_local': True}),
        ('files.delete.recursive', 'controller.files', 'delete_recursive', ('f-1', True), {}),
        ('remote_store.delete', 'controller.remote_store', 'delete', ('s-1', True), {}),
    ],
)
def test_confirm_accept_routes_representative_actions(kind, target, method, args, kwargs):
    ctrl, window = _ctrl()
    obj = window
    for part in target.split('.'):
        obj = getattr(obj, part)

    ctrl.accept(kind, 'ctx-1' if kind == 'ctx.delete' else args[0])

    getattr(obj, method).assert_called_once_with(*args, **kwargs)
    window.ui.dialog['confirm'].close.assert_called_once_with()


def test_confirm_accept_ctx_chain_validates_pair():
    ctrl, window = _ctrl()
    ctrl.accept('ctx.delete_item_chain', ('a', 'b'))
    window.controller.ctx.delete_item_chain.assert_called_once_with('a', 'b', True)

    window.controller.ctx.delete_item_chain.reset_mock()
    ctrl.accept('ctx.delete_item_chain', ('only-one',))
    window.controller.ctx.delete_item_chain.assert_not_called()


def test_confirm_accept_db_error_is_reported_without_escaping():
    ctrl, window = _ctrl()
    error = RuntimeError('db failed')
    window.core.db.viewer.delete_row.side_effect = error

    ctrl.accept('db.delete_row', {'table': 'x', 'row_id': 1})

    window.core.debug.error.assert_called_once_with(error)
    window.ui.dialogs.alert.assert_called_once_with(error)


def test_confirm_dismiss_editor_and_selection_routes():
    ctrl, window = _ctrl()
    editor = MagicMock()
    window.tools.get.return_value = editor

    ctrl.dismiss('editor.changed.open', 'x.py')
    editor.open_file.assert_called_once_with(id='x.py', force=True)

    ctrl.dismiss('ctx.delete', 'ctx')
    window.controller.ctx.select_by_current.assert_called_once_with()
    assert window.ui.dialog['confirm'].close.call_count == 2


def test_confirm_accept_rename_create_and_url_routes():
    ctrl, window = _ctrl()
    agent_builder = MagicMock()
    window.tools.get.return_value = agent_builder

    ctrl.accept_rename('ctx.group', 'g1', 'Renamed')
    window.controller.ctx.update_group_name.assert_called_once_with('g1', 'Renamed', True)

    ctrl.accept_create('mkdir', '/tmp', 'new-dir')
    window.controller.files.make_dir.assert_called_once_with('/tmp', 'new-dir')

    ctrl.accept_create('agent.builder.agent', None, 'Agent')
    agent_builder.add_agent.assert_called_once_with('Agent')

    ctrl.accept_url('attachment', None, 'https://example.test/file')
    window.controller.attachment.add_url.assert_called_once_with('https://example.test/file')


def test_confirm_dismiss_auxiliary_dialogs():
    ctrl, window = _ctrl()
    ctrl.dismiss_rename()
    ctrl.dismiss_create()
    ctrl.dismiss_url()
    window.ui.dialog['rename'].close.assert_called_once_with()
    window.ui.dialog['create'].close.assert_called_once_with()
    window.ui.dialog['url'].close.assert_called_once_with()
