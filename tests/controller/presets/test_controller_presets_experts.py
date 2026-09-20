from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.presets.experts import Experts
from pygpt_net.core.types import MODE_EXPERT


def _experts():
    window = MagicMock()
    window.ui.nodes = {
        'preset.editor.experts': MagicMock(),
        'preset.experts.available': MagicMock(),
        'preset.experts.selected': MagicMock(),
    }
    window.ui.tabs = {'preset.editor.tabs': MagicMock()}
    ctrl = Experts(window)
    window.controller.presets.editor.current = 'agent-1'
    window.controller.presets.editor.TAB_IDX = {'experts': 3}
    return ctrl, window


def test_experts_current_agent_and_active_state():
    ctrl, window = _experts()
    window.core.presets.get_by_uuid.return_value = SimpleNamespace(experts=['e1'])
    assert ctrl.get_current_agent_id() == 'agent-1'
    assert ctrl.is_active('e1') is True
    assert ctrl.is_active('e2') is False

    window.controller.presets.editor.current = None
    assert ctrl.is_active('e1') is False


def test_experts_update_list_filters_current_and_active_experts():
    ctrl, window = _experts()
    e1 = SimpleNamespace(uuid='e1')
    e2 = SimpleNamespace(uuid='e2')
    current = SimpleNamespace(uuid='current-x')
    agent = SimpleNamespace(experts=['e1'])
    window.core.presets.get_by_mode.return_value = {'current.foo': current, 'one': e1, 'two': e2}
    window.core.presets.get_by_uuid.side_effect = lambda uuid: {'agent-1': agent, 'e1': e1}.get(uuid)

    ctrl.update_list()

    window.core.presets.get_by_mode.assert_called_once_with(MODE_EXPERT)
    window.ui.nodes['preset.editor.experts'].update_available.assert_called_once_with({'two': e2})
    window.ui.nodes['preset.editor.experts'].update_selected.assert_called_once_with({'e1': e1})


def test_experts_selection_resolves_tooltip_then_fallback_and_deduplicates():
    ctrl, window = _experts()
    ix1, ix2, ix3 = MagicMock(), MagicMock(), MagicMock()
    ix1.data.return_value = 'e1'
    ix2.data.return_value = None
    ix2.row.return_value = 2
    ix3.data.return_value = 'e1'
    model = MagicMock()
    model.selectedRows.return_value = [ix1, ix2, ix3]
    window.ui.nodes['preset.experts.available'].selectionModel.return_value = model
    fallback = MagicMock(return_value='e2')

    assert ctrl._selected_uuids_from_view('preset.experts.available', fallback) == ['e1', 'e2']
    fallback.assert_called_once_with(2)


def test_experts_add_and_remove_multiple_selected_without_ui_index_dependency():
    ctrl, window = _experts()
    window.core.presets.exists_uuid.return_value = True
    agent = SimpleNamespace(experts=[])
    window.core.presets.get_by_uuid.return_value = agent
    ctrl.selected_available_uuids = ['e1', 'e2']
    ctrl.is_active = MagicMock(return_value=False)
    ctrl.update_list = MagicMock()

    ctrl.add_expert()
    assert window.core.presets.add_expert.call_count == 2
    ctrl.update_list.assert_called_once_with()

    ctrl.update_list.reset_mock()
    ctrl.selected_selected_uuids = ['e1', 'e2']
    ctrl.is_active.return_value = True
    ctrl.remove_expert()
    assert window.core.presets.remove_expert.call_count == 2
    ctrl.update_list.assert_called_once_with()


def test_experts_add_requires_saved_agent_when_current_is_missing():
    ctrl, window = _experts()
    window.controller.presets.editor.current = None
    ctrl.add_expert()
    window.controller.presets.editor.save.assert_called_once_with(close=False)


def test_experts_update_tab_uses_count_and_translation():
    ctrl, window = _experts()
    window.core.presets.get_by_uuid.return_value = SimpleNamespace(experts=['a', 'b'])
    with patch('pygpt_net.controller.presets.experts.trans', side_effect=lambda key: 'Experts'):
        ctrl.update_tab()
    window.ui.tabs['preset.editor.tabs'].setTabText.assert_called_once_with(3, 'Experts (2)')


def test_experts_refresh_is_safe_noop():
    ctrl, _ = _experts()
    assert ctrl.refresh() is None


def test_experts_change_selection_methods_use_view_resolver():
    ctrl, _ = _experts()
    ctrl._selected_uuids_from_view = MagicMock(side_effect=[['a'], ['b']])
    ctrl.change_available()
    ctrl.change_selected()
    assert ctrl.selected_available_uuids == ['a']
    assert ctrl.selected_selected_uuids == ['b']


def test_experts_current_selection_and_index_resolvers():
    ctrl, window = _experts()
    window.ui.nodes['preset.experts.available'].selectionModel().currentIndex().row.return_value = 1
    window.ui.nodes['preset.experts.selected'].selectionModel().currentIndex().row.return_value = 0
    ctrl.get_available_by_idx = MagicMock(return_value='e2')
    ctrl.get_selected_by_idx = MagicMock(return_value='e1')
    assert ctrl.get_current_available() == 'e2'
    assert ctrl.get_current_selected() == 'e1'


def test_experts_raw_index_resolvers_filter_current_and_active():
    ctrl, window = _experts()
    e1, e2 = SimpleNamespace(uuid='e1'), SimpleNamespace(uuid='e2')
    window.core.presets.get_by_mode.return_value = {'current.x': SimpleNamespace(uuid='c'), 'one': e1, 'two': e2}
    ctrl.is_active = MagicMock(side_effect=lambda uuid: uuid == 'e1')
    assert Experts.get_available_by_idx(ctrl, 0) == 'e2'

    agent = SimpleNamespace(experts=['e1', 'e2'])
    window.core.presets.get_by_uuid.return_value = agent
    assert Experts.get_selected_by_idx(ctrl, 1) == 'e2'
    assert Experts.get_selected_by_idx(ctrl, 9) is None
