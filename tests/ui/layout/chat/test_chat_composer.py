from PySide6.QtWidgets import QWidget, QTabWidget
from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.ui.ui import UI
from pygpt_net.ui.widget.tabs.Input import ChatComposer


def test_composer_legacy_controls_and_optional_media_prompt(qapp):
    page, extra = QWidget(), QWidget()
    composer = ChatComposer(None, page, extra)
    assert composer._prompt_tabs.isHidden()
    assert not composer.findChildren(QTabWidget)
    assert extra.isHidden()
    for index in (1, 2, 3):
        composer.setTabVisible(index, True)
        composer.setCurrentIndex(index)
        assert composer.currentWidget() is page
        assert composer.currentIndex() == 0
        assert not composer.isTabVisible(index)
    composer.setTabVisible(4, True)
    assert not composer._prompt_tabs.isHidden()
    composer.setCurrentIndex(4)
    assert composer.currentWidget() is extra
    composer.setTabVisible(4, False)
    assert composer.currentWidget() is page
    composer.close()


def test_token_counter_updates_once_for_unchanged_values():
    editor = MagicMock()
    editor.toPlainText.return_value = "Hello"
    editor.serialize_mentions.return_value = "Hello"
    counter = MagicMock()
    window = SimpleNamespace(
        ui=SimpleNamespace(nodes={'input': editor, 'input.counter': counter},
                           tabs={}),
        core=SimpleNamespace(tokens=SimpleNamespace(
            get_current=MagicMock(return_value=(5, 10, 0, 20, 0, 0, 35, 1000, 0)))),
        controller=SimpleNamespace(chat=SimpleNamespace(attachment=SimpleNamespace(
            get_current_tokens=MagicMock(return_value=0)))),
    )
    controller = UI.__new__(UI)
    controller.window = window
    controller._tokens_update_timer = MagicMock()
    controller._last_input_string = None
    controller._last_input_counter_tooltip = None
    controller.update_tokens()
    controller.update_tokens()
    counter.setText.assert_called_once_with('~ 35 / 1k')
    counter.setToolTip.assert_called_once()
