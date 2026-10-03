from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt, QEventLoop, QTimer
import pytest

from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QWidget, QPushButton

from pygpt_net.controller.toolbar import Toolbar


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def finish_animation():
    loop = QEventLoop()
    QTimer.singleShot(250, loop.quit)
    loop.exec()


def test_toolbox_toggle_animates_and_hides_splitter_handle(qapp):
    window = QMainWindow()
    splitter = QSplitter(Qt.Horizontal)
    toolbox, contexts, chat = QWidget(), QWidget(), QWidget()
    for widget in (toolbox, contexts, chat):
        splitter.addWidget(widget)
    contexts.setMinimumWidth(200)
    toolbox.hide()
    button = QPushButton()
    button.setCheckable(True)
    values = {}
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    config.set.side_effect = lambda key, value: values.__setitem__(key, value)
    window.core = SimpleNamespace(config=config)
    window.ui = SimpleNamespace(splitters={'main': splitter}, parts={'toolbox': toolbox},
                                nodes={'toolbar.toolbox': button})
    window.setCentralWidget(splitter)
    window.resize(1000, 500)
    window.show()
    qapp.processEvents()
    splitter.setSizes([0, 220, 780])
    controller = Toolbar(window)
    original_context_width = splitter.sizes()[1]
    assert not splitter.handle(1).isVisible()
    controller.toggle_toolbox()
    finish_animation()
    assert toolbox.isVisible()
    assert splitter.handle(1).isVisible()
    assert splitter.sizes()[0] > 200
    assert abs(splitter.sizes()[1] - original_context_width) < 15
    assert button.isChecked()
    splitter.setSizes([300, 220, 480])
    width = splitter.sizes()[0]
    controller.toggle_toolbox()
    finish_animation()
    assert toolbox.isHidden()
    assert not splitter.handle(1).isVisible()
    assert not button.isChecked()
    assert values['layout.toolbox.width'] == width
    controller.toggle_toolbox()
    finish_animation()
    assert abs(splitter.sizes()[0] - width) < 15
    controller.toggle_toolbox()
    controller.toggle_toolbox()
    finish_animation()
    assert toolbox.isVisible()
    assert button.isChecked()
    window.close()
