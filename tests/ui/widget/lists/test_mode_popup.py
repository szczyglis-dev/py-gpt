from PySide6.QtWidgets import QLineEdit
from pygpt_net.ui.widget.lists.mode_combo import ModePopupCombo


def test_mode_popup_without_radio_or_search(qapp, monkeypatch):
    monkeypatch.setattr('PySide6.QtWidgets.QMenu.popup', lambda *args: None)
    combo = ModePopupCombo()
    combo.addSection('Modes')
    combo.addItem('Chat', 'chat')
    combo.addItem('Agents', 'agent')
    combo.setCurrentIndex(1)
    combo.setFixedWidth(220)
    combo.showPopup()
    menu = combo._popup_menu
    assert not menu.findChildren(QLineEdit)
    choices = [action for action in menu.actions() if action.isEnabled() and not action.isSeparator()]
    assert len(choices) == 2
    assert menu.width() == combo.width()
    assert choices[0].isChecked()
    assert not choices[1].isChecked()
    assert 'border: none; background-color: transparent' in menu.styleSheet()
    assert choices[0].font().bold()
    assert not choices[1].font().bold()
    choices[1].trigger()
    assert combo.currentData() == 'agent'
    combo.hidePopup()
    menu.aboutToHide.emit()
    assert combo._popup_menu is None
    combo.showPopup()
    choices = [action for action in combo._popup_menu.actions()
               if action.isEnabled() and not action.isSeparator()]
    assert not choices[0].font().bold()
    assert choices[1].font().bold()
    combo._popup_menu.aboutToHide.emit()
    combo.close()
