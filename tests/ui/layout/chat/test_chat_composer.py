from PySide6.QtWidgets import QApplication, QWidget, QTabBar, QTabWidget
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.ui.ui import UI
from pygpt_net.ui.widget.tabs.Input import ChatComposer


def test_composer_has_no_tabs_and_legacy_controls_cannot_switch_away():
    app = QApplication.instance() or QApplication([])
    page, extra = QWidget(), QWidget()
    composer = ChatComposer(None, page, extra)
    assert not composer.findChildren(QTabBar)
    assert not composer.findChildren(QTabWidget)
    assert extra.isHidden()
    for index in (1, 2, 3):
        composer.setTabVisible(index, True)
        composer.setCurrentIndex(index)
        assert composer.currentWidget() is page
        assert composer.currentIndex() == 0
        assert not composer.isTabVisible(index)
    composer.setTabVisible(4, True)
    assert not extra.isHidden()
    assert composer.currentWidget() is page
    composer.close()


def test_token_counter_updates_with_real_tabless_composer():
    app = QApplication.instance() or QApplication([])
    composer = ChatComposer(None, QWidget(), QWidget())
    editor = MagicMock()
    editor.toPlainText.return_value = "Hello"
    editor.serialize_mentions.return_value = "Hello"
    counter = MagicMock()
    window = SimpleNamespace(
        ui=SimpleNamespace(nodes={'input': editor, 'input.counter': counter},
                           tabs={'input': composer}),
        core=SimpleNamespace(tokens=SimpleNamespace(
            get_current=MagicMock(return_value=(5, 10, 0, 20, 0, 0, 35, 1000, 0)))),
        controller=SimpleNamespace(chat=SimpleNamespace(attachment=SimpleNamespace(
            get_current_tokens=MagicMock(return_value=0)))),
    )
    controller = UI(window)
    controller.update_tokens()
    controller.update_tokens()
    counter.setText.assert_called_once_with('~ 35 / 1k')
    counter.setToolTip.assert_called_once()
    assert not composer.findChildren(QTabBar)
    composer.close()
