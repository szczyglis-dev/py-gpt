from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.lists.model_combo import CompactModelCombo


@pytest.mark.parametrize('grouped', [True, False])
def test_provider_menu_keeps_selection_and_omits_empty_providers(qapp, monkeypatch, grouped):
    monkeypatch.setattr('PySide6.QtWidgets.QMenu.popup', lambda *args: None)
    config = {'model': 'b', 'model.group_providers': grouped}
    window = SimpleNamespace(
        core=SimpleNamespace(config=SimpleNamespace(get=config.get)),
        controller=SimpleNamespace(model=SimpleNamespace(select=MagicMock())),
        ui=SimpleNamespace(nodes={}),
    )
    widget = CompactModelCombo(window)
    widget.set_keys({'separator::empty': 'Empty', 'separator::one': 'One',
                     'a': 'Model A', 'b': 'Model B',
                     'separator::two': 'Two', 'c': 'Model C'})
    widget._show_menu()
    menu = widget._menu
    if grouped:
        assert [action.text() for action in menu.actions()] == ['One', 'Two']
        models = menu.actions()[0].menu().actions()
        assert [action.text() for action in models] == ['Model A', 'Model B']
        assert models[1].isChecked()
    else:
        assert all(action.menu() is None for action in menu.actions())
        models = [action for action in menu.actions() if action.isCheckable()]
        assert [action.text() for action in models] == ['Model A', 'Model B', 'Model C']
        assert models[1].isChecked()
    models[0].trigger()
    window.controller.model.select.assert_called_once_with('a')
    menu.close()
    widget.deleteLater()
