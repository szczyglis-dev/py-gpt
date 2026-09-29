from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.assistant.editor import Editor


def _editor():
    window = MagicMock()
    window.ui.config = {
        'assistant': {
            'vector_store': MagicMock(),
            'tool.function': MagicMock(items=[]),
            'name': MagicMock(),
        }
    }
    return Editor(window), window


def test_assistant_editor_options_and_setup_register_dictionary():
    ctrl, window = _editor()
    assert ctrl.get_options() is ctrl.options
    assert ctrl.get_option('name') is ctrl.options['name']
    assert ctrl.get_option('missing') is None
    ctrl.update_store_list = MagicMock()
    ctrl.setup()
    window.ui.dialogs.register_dictionary.assert_called_once_with(
        'tool.function', 'assistant', ctrl.options['tool.function']
    )
    ctrl.update_store_list.assert_called_once_with()


def test_assistant_editor_store_selection_helpers_skip_hidden_stores():
    ctrl, window = _editor()
    stores = {'hidden': SimpleNamespace(name='H'), 's1': SimpleNamespace(name='Store')}
    window.core.remote_store.openai.get_all.return_value = stores
    window.core.remote_store.openai.is_hidden.side_effect = lambda sid: sid == 'hidden'
    window.controller.config.get_value.return_value = 2
    window.ui.config['assistant']['vector_store'].combo.itemData.return_value = 's1'
    assert ctrl.get_selected_store_id() == 's1'
    assert ctrl.get_choice_idx_by_id('s1') == 1
    assert ctrl.get_choice_idx_by_id('missing') == 0


def test_assistant_editor_update_store_list_builds_visible_combo_only():
    ctrl, window = _editor()
    stores = {
        'a': SimpleNamespace(name='Alpha'),
        'b': SimpleNamespace(name=''),
        'hidden': SimpleNamespace(name='Hidden'),
    }
    window.core.remote_store.openai.get_all.return_value = stores
    window.core.remote_store.openai.is_hidden.side_effect = lambda sid: sid == 'hidden'
    ctrl.get_selected_store_id = MagicMock(return_value=None)
    ctrl.update_store_list()
    window.controller.config.update_combo.assert_called_once_with(
        'assistant', 'vector_store', {'--': '--', 'a': 'Alpha', 'b': 'b'}
    )
    window.controller.config.apply_value.assert_called_once()


def test_assistant_editor_edit_and_close_delegate_selection():
    ctrl, window = _editor()
    window.core.assistants.get_by_idx.return_value = 'a1'
    ctrl.init = MagicMock()
    ctrl.edit(3)
    ctrl.init.assert_called_once_with('a1')
    window.ui.dialogs.open_editor.assert_called_once_with('editor.assistants', 3, width=900)

    window.core.config.get.return_value = 'a1'
    ctrl.close()
    window.ui.dialogs.close.assert_called_once_with('editor.assistants')
    window.controller.assistant.select_by_id.assert_called_once_with('a1')


def test_assistant_editor_import_functions_replaces_existing_and_adds_new():
    ctrl, window = _editor()
    field = window.ui.config['assistant']['tool.function']
    field.items = [{'name': 'same', 'params': '{}', 'desc': 'old'}]
    window.core.command.as_native_functions.return_value = [
        {'name': 'same', 'params': '{"x":1}', 'desc': 'new'},
        {'name': 'extra', 'params': '{}', 'desc': 'added'},
    ]
    ctrl.import_functions(True)
    assert field.items == [
        {'name': 'same', 'params': '{"x":1}', 'desc': 'new'},
        {'name': 'extra', 'params': '{}', 'desc': 'added'},
    ]
    field.model.updateData.assert_called_once_with(field.items)


def test_assistant_editor_import_and_clear_require_confirmation_when_not_forced():
    ctrl, window = _editor()
    ctrl.import_functions(False)
    ctrl.clear_functions(False)
    assert window.ui.dialogs.confirm.call_count == 2

    field = window.ui.config['assistant']['tool.function']
    field.items = [{'name': 'x'}]
    ctrl.clear_functions(True)
    assert field.items == []
    field.model.updateData.assert_called_with([])


def test_assistant_editor_assign_data_normalizes_model_function_defaults_and_store():
    ctrl, window = _editor()
    values = {
        'model': '_', 'name': 'Assistant', 'description': None, 'instructions': 'Do work',
        'tool.code_interpreter': True, 'tool.file_search': False,
        'tool.function': [
            {'name': '', 'params': '', 'desc': ''},
            {'name': 'fn', 'params': '', 'desc': None},
        ],
    }
    window.controller.config.get_value.side_effect = lambda **kw: values[kw['key']]
    ctrl.get_selected_store_id = MagicMock(return_value='store-1')
    assistant = SimpleNamespace()

    ctrl.assign_data(assistant)

    assert assistant.name == 'Assistant'
    assert assistant.model is None
    assert assistant.tools['code_interpreter'] is True
    assert assistant.tools['file_search'] is False
    assert assistant.tools['function'] == [{
        'name': 'fn',
        'params': '{"type": "object", "properties": {}}',
        'desc': '',
    }]
    assert assistant.vector_store == 'store-1'


def test_assistant_editor_save_rejects_empty_name_or_model_before_api_call():
    ctrl, window = _editor()
    values = {'id': '', 'name': '', 'model': 'm'}
    window.controller.config.get_value.side_effect = lambda **kw: values[kw['key']]
    ctrl.save()
    window.ui.dialogs.alert.assert_called_once()
    window.controller.assistant.create.assert_not_called()


def test_assistant_editor_save_new_assistant_mocks_qt_and_api_controller():
    ctrl, window = _editor()
    values = {'id': '', 'name': 'Name', 'model': 'model'}
    window.controller.config.get_value.side_effect = lambda **kw: values.get(kw['key'], None)
    assistant = SimpleNamespace(id='new-id')
    window.controller.assistant.create.return_value = assistant
    ctrl.assign_data = MagicMock()
    with patch('pygpt_net.controller.assistant.editor.QApplication.processEvents'):
        ctrl.save()
    window.core.assistants.add.assert_called_once_with(assistant)
    ctrl.assign_data.assert_called_once_with(assistant)
    window.core.assistants.save.assert_called_once_with()
    window.controller.assistant.select_by_id.assert_called_once_with('new-id')
