from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QMainWindow

from pygpt_net.controller.toolbar import Toolbar
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools import Tools
from pygpt_net.tools.base import BaseTool, ToolToolbarItem
from pygpt_net.tools.files import Files
from pygpt_net.tools.notepad import Notepad
from pygpt_net.tools.painter import Painter
from pygpt_net.ui.toolbar import LeftToolbar


class CustomTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = 'custom'
        self.clicked = []

    def get_toolbar(self):
        return [
            ToolToolbarItem(':/icons/build.svg', 'custom.first', lambda: self.clicked.append('first')),
            ToolToolbarItem(':/icons/add.svg', 'custom.second', lambda: self.clicked.append('second'), id='extra'),
        ]


@pytest.mark.parametrize("register_before_ui", [False, True])
def test_toolbar_uses_registration_order_tool_handlers_and_live_translations(qapp, monkeypatch, register_before_ui):
    import pygpt_net.tools.base as base
    language = ['one']
    monkeypatch.setattr(base, 'trans', lambda key, domain=None: language[0] + ':' + key)
    window = QMainWindow()
    tabs = MagicMock()
    tabs.is_split_screen_enabled.return_value = False
    window.controller = SimpleNamespace(tabs=tabs)
    controller = window.controller.toolbar = Toolbar(window)
    controller.toggle_toolbox = MagicMock()
    window.ui = SimpleNamespace(nodes={})
    window.tools = Tools(window)
    custom = CustomTool()
    tools = (Files(), Notepad(), Painter(), BaseTool(), custom)
    if register_before_ui:
        for tool in tools:
            window.tools.register(tool)
    toolbar = LeftToolbar(window)
    if not register_before_ui:
        assert set(window.ui.nodes) == {'toolbar.home', 'toolbar.toolbox'}
        for tool in tools:
            window.tools.register(tool)
    keys = [next(name for name, node in window.ui.nodes.items() if node is widget)
            for index in range(toolbar.layout().count())
            if (widget := toolbar.layout().itemAt(index).widget()) is not None]
    assert keys == ['toolbar.home', 'toolbar.files', 'toolbar.notepad', 'toolbar.painter',
                    'toolbar.custom', 'toolbar.custom.extra', 'toolbar.toolbox']
    for name in ('files', 'notepad', 'painter'):
        button = window.ui.nodes['toolbar.' + name]
        assert not button.icon().isNull()
        button.click()
        tabs.open_or_activate.assert_called_with(Tab.TAB_TOOL, name)
    window.ui.nodes['toolbar.home'].click()
    tabs.open_or_activate.assert_called_with(Tab.TAB_CHAT, create=False)
    window.ui.nodes['toolbar.toolbox'].click()
    controller.toggle_toolbox.assert_called_once()
    window.ui.nodes['toolbar.custom'].click()
    window.ui.nodes['toolbar.custom.extra'].click()
    assert custom.clicked == ['first', 'second']
    assert window.ui.nodes['toolbar.custom'].toolTip() == 'one:custom.first'
    language[0] = 'two'
    window.tools.apply_lang_mappings()
    assert window.ui.nodes['toolbar.custom'].toolTip() == 'two:custom.first'
    assert window.ui.nodes['toolbar.custom.extra'].toolTip() == 'two:custom.second'
    replacement = CustomTool()
    window.tools.register(replacement)
    window.ui.nodes['toolbar.custom'].click()
    assert replacement.clicked == ['first']
    assert custom.clicked == ['first', 'second']
    # Re-registration replaces entries in place instead of duplicating buttons.
    assert toolbar.layout().count() == 8  # Seven buttons and the spacer.
    assert toolbar.layout().itemAt(4).widget() is window.ui.nodes['toolbar.custom']
    assert toolbar.layout().itemAt(5).widget() is window.ui.nodes['toolbar.custom.extra']
    window.deleteLater()
    QCoreApplication.sendPostedEvents(window, QEvent.DeferredDelete)


def test_base_tool_does_not_add_toolbar_buttons(qapp):
    assert BaseTool().get_toolbar() == []
