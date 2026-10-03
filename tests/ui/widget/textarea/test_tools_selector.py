from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtWidgets import QWidget, QPushButton, QCheckBox
from pygpt_net.ui.widget.textarea.input import ChatInput


def test_tools_menu_has_independent_radio_groups_and_uses_existing_toggles(qapp, monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.input.trans', lambda key: key)
    widget = QWidget()
    widget._tools_menu = None
    widget._icons_right = {'web': QPushButton(widget)}
    widget.update_tools_selector = MagicMock()
    widget._clear_tools_menu = lambda: ChatInput._clear_tools_menu(widget)
    widget.set_tools_enabled = lambda enabled: ChatInput.set_tools_enabled(widget, enabled)
    widget.set_web_enabled = lambda enabled: ChatInput.set_web_enabled(widget, enabled)
    box = QCheckBox()
    legacy_toggle = MagicMock()
    box.toggled.connect(legacy_toggle)
    remote = SimpleNamespace(enabled_global={'web_search': False}, toggle=MagicMock())
    remote.toggle.side_effect = lambda key: remote.enabled_global.__setitem__(key, not remote.enabled_global[key])
    config = MagicMock()
    config.get.return_value = False
    widget.window = SimpleNamespace(
        ui=SimpleNamespace(nodes={'cmd.enabled': SimpleNamespace(box=box)}),
        core=SimpleNamespace(config=config),
        controller=SimpleNamespace(chat=SimpleNamespace(remote_tools=remote)),
    )
    widget.show()
    ChatInput.action_tools_menu(widget)
    menu = widget._tools_menu
    actions = [action for action in menu.actions() if action.isCheckable()]
    assert len(actions) == 4
    all_actions = menu.actions()
    separators = [i for i, action in enumerate(all_actions) if action.isSeparator()]
    assert len(separators) == 1
    assert all_actions[separators[0] + 1].text() == 'input.internet.header'
    assert actions[0].actionGroup() is actions[1].actionGroup()
    assert actions[2].actionGroup() is actions[3].actionGroup()
    assert actions[0].actionGroup() is not actions[2].actionGroup()
    assert actions[1].isChecked() and actions[3].isChecked()
    actions[0].trigger()
    legacy_toggle.assert_called_once_with(True)
    assert box.isChecked()
    assert actions[3].isChecked()  # Tools doesn't change Internet.
    actions[2].trigger()
    remote.toggle.assert_called_once_with('web_search')
    ChatInput.set_web_enabled(widget, True)
    remote.toggle.assert_called_once()  # Selecting the existing radio value is a no-op.
    actions[1].trigger()
    assert not box.isChecked()
    assert remote.enabled_global['web_search']
    menu.close()
    widget.close()


def test_tools_button_title_tracks_tools_choice(qapp, monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.input.trans', lambda key: key)
    button = QPushButton()
    config = MagicMock()
    widget = SimpleNamespace(
        _icons_right={'web': button}, _icon_meta_right={'web': {}},
        window=SimpleNamespace(core=SimpleNamespace(config=config)),
        _fit_right_text_button=MagicMock(), _update_icon_bar_geometry_right=MagicMock(),
        _apply_margins=MagicMock(),
    )
    for value, title in ((True, 'input.tools.enabled'), (False, 'input.tools.disabled')):
        config.get.return_value = value
        ChatInput.update_tools_selector(widget)
        assert button.text() == title + '  ▴'
    button.deleteLater()
