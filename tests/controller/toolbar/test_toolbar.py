from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.toolbar import Toolbar
from pygpt_net.core.tabs.tab import Tab


@pytest.mark.parametrize("toolbox_first", [True, False])
def test_toolbox_toggle_remembers_width_and_preserves_context_column(monkeypatch, toolbox_first):
    from pygpt_net.ui.layout import sidebar
    monkeypatch.setattr(sidebar, "TOOLBOX_FIRST", toolbox_first)
    ti, ci = (0, 1) if toolbox_first else (1, 0)
    toolbox, contexts = MagicMock(), MagicMock()
    sizes = sidebar.pane_sizes(0, 220, 780)
    splitter = MagicMock()
    splitter.indexOf.side_effect = lambda widget: ti if widget is toolbox else ci
    splitter.sizes.side_effect = lambda: list(sizes)
    splitter.setSizes.side_effect = lambda value: sizes.__setitem__(slice(None), value)
    values = {}
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    config.set.side_effect = lambda key, value: values.__setitem__(key, value)
    button = MagicMock()
    window = SimpleNamespace(core=SimpleNamespace(config=config), ui=SimpleNamespace(
        splitters={'main': splitter}, parts={'toolbox': toolbox, 'ctx': contexts},
        nodes={'toolbar.toolbox': button}))
    factory = MagicMock(side_effect=lambda parent: MagicMock())
    monkeypatch.setattr('pygpt_net.controller.toolbar.QVariantAnimation', factory)
    controller = Toolbar(window)

    def toggle_and_finish():
        controller.toggle_toolbox()
        animation = controller._animation
        target = animation.setEndValue.call_args.args[0]
        animation.valueChanged.connect.call_args.args[0](target)
        animation.finished.connect.call_args.args[0]()
        assert sizes[ci] == 220

    toggle_and_finish()
    assert sizes[ti] == 260
    toolbox.show.assert_called_once_with()
    button.setChecked.assert_called_with(True)
    sizes[:] = sidebar.pane_sizes(300, 220, 480)
    toggle_and_finish()
    assert sizes[ti] == 0
    assert values['layout.toolbox.width'] == 300
    toolbox.hide.assert_called_once_with()
    button.setChecked.assert_called_with(False)
    toggle_and_finish()
    assert sizes[ti] == 300
    button.setChecked.assert_called_with(True)


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
    from pygpt_net.tools.files import Files
    from pygpt_net.tools.notepad import Notepad
    from pygpt_net.tools.painter import Painter
    window.controller.toolbar = Toolbar(window)
    tool = {'files': Files, 'notepad': Notepad, 'painter': Painter}[action]()
    tool.window = window
    tool.get_toolbar()[0].handler()
    if collapse:
        tabs.disable_split_screen.assert_called_once_with()
        tabs.open_or_activate.assert_not_called()
    else:
        tabs.open_or_activate.assert_called_once_with(tab_type, action) if action in ("painter", "files", "notepad") else tabs.open_or_activate.assert_called_once_with(tab_type)
        tabs.disable_split_screen.assert_not_called()
