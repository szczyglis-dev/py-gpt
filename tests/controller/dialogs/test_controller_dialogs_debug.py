from unittest.mock import MagicMock, patch

from pygpt_net.controller.dialogs.debug import Debug


def _debug():
    ctrl = Debug.__new__(Debug)
    ctrl.window = MagicMock()
    ctrl.is_realtime = False
    ctrl.ids = ['x']
    ctrl.workers = {'x': MagicMock()}
    ctrl.models = {'x': MagicMock()}
    ctrl.initialized = {'x': False}
    ctrl.active = {'x': False}
    ctrl.idx = {'x': 0}
    ctrl.counters = {}
    ctrl.window.ui.debug = {'x': MagicMock()}
    return ctrl


def test_debug_refresh_only_touches_known_id():
    ctrl = _debug()
    ctrl.initialized['x'] = True
    ctrl.refresh('x')
    assert ctrl.initialized['x'] is False
    ctrl.refresh('missing')
    assert 'missing' not in ctrl.initialized


def test_debug_begin_uses_mocked_clock_and_resets_changed_row_count():
    ctrl = _debug()
    model = ctrl.models['x']
    model.rowCount.return_value = 3
    ctrl.counters['x'] = 2
    with patch('pygpt_net.controller.dialogs.debug.time.strftime', return_value='2026-01-02 03:04:05'), \
         patch('pygpt_net.controller.dialogs.debug.time.localtime', return_value=object()):
        ctrl.begin('x')
    ctrl.window.ui.debug['x'].last_update_label.setText.assert_called_once_with(
        'Last update: 2026-01-02 03:04:05'
    )
    model.removeRows.assert_called_once_with(0, 3)
    ctrl.window.ui.debug['x'].setUpdatesEnabled.assert_called_with(False)
    assert ctrl.idx['x'] == 0


def test_debug_begin_skips_initialized_active_non_realtime_view():
    ctrl = _debug()
    ctrl.initialized['x'] = True
    ctrl.active['x'] = True
    ctrl.begin('x')
    ctrl.window.ui.debug['x'].setModel.assert_not_called()


def test_debug_end_marks_initialized_and_restores_updates():
    ctrl = _debug()
    ctrl.idx['x'] = 7
    ctrl.end('x')
    assert ctrl.counters['x'] == 7
    assert ctrl.initialized['x'] is True
    ctrl.window.ui.debug['x'].on_data_end.assert_called_once_with()
    ctrl.window.ui.debug['x'].setUpdatesEnabled.assert_called_once_with(True)


def test_debug_add_inserts_when_not_initialized():
    ctrl = _debug()
    model = ctrl.models['x']
    model.rowCount.return_value = 2
    model.index.side_effect = lambda row, col: ('idx', row, col)
    ctrl.add('x', 'key', 'value')
    model.insertRow.assert_called_once_with(2)
    assert model.setData.call_count == 2
    assert ctrl.idx['x'] == 1


def test_debug_getters_worker_update_and_active_helpers():
    ctrl = _debug()
    assert ctrl.get_ids() == ['x']
    assert ctrl.get_workers() is ctrl.workers
    ctrl.update_worker('x')
    ctrl.workers['x'].update.assert_called_once_with()
    ctrl.update_worker('missing')
    assert ctrl.is_active('missing') is False
    assert ctrl.is_active('x') is False


def test_debug_show_hide_open_and_close_only_known_windows():
    ctrl = _debug()
    ctrl.show('x')
    assert ctrl.active['x'] is True
    ctrl.window.ui.dialogs.open.assert_called_once_with('debug.x', width=800, height=600)
    ctrl.hide('x')
    assert ctrl.active['x'] is False
    ctrl.window.ui.dialogs.close.assert_called_once_with('debug.x')


def test_debug_create_model_uses_qt_model_mock_instead_of_real_widget_model():
    ctrl = _debug()
    model = MagicMock()
    with patch('pygpt_net.controller.dialogs.debug.QStandardItemModel', return_value=model) as factory:
        assert ctrl.create_model('parent') is model
    factory.assert_called_once_with(0, 2, 'parent')
    assert model.setHeaderData.call_count == 2


def test_debug_set_realtime_updates_shared_flag():
    ctrl = _debug()
    ctrl.set_realtime('x', True)
    assert ctrl.is_realtime is True
    ctrl.set_realtime('x', False)
    assert ctrl.is_realtime is False
