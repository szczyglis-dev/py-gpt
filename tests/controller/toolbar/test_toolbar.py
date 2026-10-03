from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt, QEventLoop, QTimer
import pytest

from PySide6.QtWidgets import QApplication, QMainWindow, QSplitter, QWidget, QPushButton

from pygpt_net.controller.toolbar import Toolbar
from pygpt_net.core.tabs.tab import Tab


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


def finish_animation():
    loop = QEventLoop()
    QTimer.singleShot(250, loop.quit)
    loop.exec()


@pytest.mark.parametrize("toolbox_first", [True, False])
def test_toolbox_toggle_animates_and_hides_splitter_handle(qapp, monkeypatch, toolbox_first):
    from pygpt_net.ui.layout import sidebar
    monkeypatch.setattr(sidebar, "TOOLBOX_FIRST", toolbox_first)
    ti, ci = (0, 1) if toolbox_first else (1, 0)
    window = QMainWindow()
    splitter = QSplitter(Qt.Horizontal)
    toolbox, contexts, chat = QWidget(), QWidget(), QWidget()
    for widget in ((toolbox, contexts, chat) if toolbox_first else (contexts, toolbox, chat)):
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
    window.ui = SimpleNamespace(splitters={'main': splitter}, parts={'toolbox': toolbox, 'ctx': contexts},
                                nodes={'toolbar.toolbox': button})
    window.setCentralWidget(splitter)
    window.resize(1000, 500)
    window.show()
    qapp.processEvents()
    splitter.setSizes(sidebar.pane_sizes(0, 220, 780))
    controller = Toolbar(window)
    original_context_width = splitter.sizes()[ci]
    if toolbox_first:
        assert not splitter.handle(1).isVisible()
    controller.toggle_toolbox()
    finish_animation()
    assert toolbox.isVisible()
    assert splitter.handle(1).isVisible()
    assert splitter.sizes()[ti] > 200
    assert abs(splitter.sizes()[ci] - original_context_width) < 15
    assert button.isChecked()
    splitter.setSizes(sidebar.pane_sizes(300, 220, 480))
    width = splitter.sizes()[ti]
    controller.toggle_toolbox()
    finish_animation()
    assert toolbox.isHidden()
    if toolbox_first:
        assert not splitter.handle(1).isVisible()
    assert not button.isChecked()
    assert values['layout.toolbox.width'] == width
    controller.toggle_toolbox()
    finish_animation()
    assert abs(splitter.sizes()[ti] - width) < 15
    controller.toggle_toolbox()
    controller.toggle_toolbox()
    finish_animation()
    assert toolbox.isVisible()
    assert button.isChecked()
    window.close()


@pytest.mark.parametrize('action, tab_type', [('files', Tab.TAB_TOOL), ('notepad', Tab.TAB_TOOL), ('painter', Tab.TAB_TOOL)])
@pytest.mark.parametrize('split, selected_type, collapse', [
    (True, None, False), (False, 2, False), (True, 0, False),
    (True, 'same', True),
])
def test_tool_buttons_collapse_only_the_selected_visible_right_tool(action, tab_type,
                                                                    split, selected_type, collapse):
    tabs = MagicMock()
    selected = tab_type if selected_type == 'same' else selected_type
    tabs.get_current_by_column.return_value = (SimpleNamespace(type=selected, tool_id=action if action in ("painter", "files", "notepad") else None)
                                               if selected is not None else None)
    tabs.is_split_screen_enabled.return_value = split
    window = SimpleNamespace(controller=SimpleNamespace(tabs=tabs))
    getattr(Toolbar(window), action)()
    if collapse:
        tabs.disable_split_screen.assert_called_once_with()
        tabs.open_or_activate.assert_not_called()
    else:
        tabs.open_or_activate.assert_called_once_with(tab_type, action) if action in ("painter", "files", "notepad") else tabs.open_or_activate.assert_called_once_with(tab_type)
        tabs.disable_split_screen.assert_not_called()
