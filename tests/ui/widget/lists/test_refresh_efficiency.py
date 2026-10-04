from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtGui import QStandardItemModel
from PySide6.QtTest import QTest

from pygpt_net.controller.ui.ui import UI
from pygpt_net.ui.layout.toolbox.presets import Presets
from pygpt_net.ui.widget.lists.base_list_combo import BaseListCombo


def test_unchanged_choices_preserve_selection_and_changed_order_rebuilds(qapp):
    widget = BaseListCombo()
    choices = {'chat': 'Chat', 'agent': 'Agents'}
    widget.set_keys(choices)
    widget.set_value('agent')
    reset = MagicMock()
    widget.combo.model().modelReset.connect(reset)
    widget.set_keys(dict(choices))
    reset.assert_not_called()
    assert widget.combo.currentData() == 'agent'
    widget.set_keys(dict(reversed(list(choices.items()))))
    assert widget.combo.itemData(0) == 'agent'
    choices['chat'] = 'Conversation'
    widget.set_keys(choices)
    assert widget.combo.itemText(0) == 'Conversation'
    widget.close()


def test_preset_refresh_preserves_rows_but_updates_tooltip_and_selection_override(qapp):
    model = QStandardItemModel()
    view = MagicMock()
    view._selection_override_ids = None
    window = MagicMock()
    window.core.config.get.side_effect = lambda key: 'chat' if key == 'mode' else False
    window.ui.nodes = {'preset.presets': view}
    window.ui.models = {'preset.presets': model}
    layout = Presets(window)
    item = SimpleNamespace(name='Test', prompt='x' * 80, uuid='one', enabled=True)
    data = {'test': item}
    layout.update_presets(data)
    reset = MagicMock()
    model.modelReset.connect(reset)
    layout.update_presets(data)
    reset.assert_not_called()
    item.prompt += 'x'
    layout.update_presets(data)
    assert model.item(0).toolTip() == 'x' * 80 + '...'
    view._selection_override_ids = ['one']
    layout.update_presets(data)
    assert view._saved_selection_ids == ['one']
    assert view._selection_override_ids is None


def test_repeated_token_requests_compute_once(qapp, monkeypatch):
    compute = MagicMock()
    monkeypatch.setattr(UI, 'update_tokens', compute)
    controller = UI()
    for _ in range(10):
        controller.request_tokens_update()
    assert compute.call_count == 0
    QTest.qWait(70)
    assert compute.call_count == 1
    controller._tokens_update_timer.stop()
    controller._tokens_update_timer.deleteLater()
