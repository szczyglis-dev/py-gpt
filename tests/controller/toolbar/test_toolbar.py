from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.toolbar import Toolbar
from pygpt_net.core.tabs.tab import Tab


@pytest.mark.parametrize("position", ["left", "middle", "right"])
def test_toolbox_toggle_remembers_width_and_preserves_context_column(monkeypatch, position):
    from pygpt_net.ui.layout import sidebar
    order = sidebar.pane_order(position)
    ti, ci = order.index("toolbox"), order.index("ctx")
    toolbox, contexts = MagicMock(), MagicMock()
    sizes = sidebar.pane_sizes(0, 220, 780, position)
    splitter = MagicMock()
    splitter.indexOf.side_effect = lambda widget: ti if widget is toolbox else ci
    splitter.sizes.side_effect = lambda: list(sizes)
    splitter.setSizes.side_effect = lambda value: sizes.__setitem__(slice(None), value)
    values = {"layout.toolbox.placement": position}
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
        assert values['layout.toolbox.expanded'] is controller._toolbox_visible
        config.save.assert_called()

    toggle_and_finish()
    assert sizes[ti] == 260
    toolbox.show.assert_called_once_with()
    button.setChecked.assert_called_with(True)
    sizes[:] = sidebar.pane_sizes(300, 220, 480, position)
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


@pytest.mark.parametrize('source', ['left', 'middle', 'right'])
@pytest.mark.parametrize('destination', ['left', 'middle', 'right'])
@pytest.mark.parametrize('visible', [False, True])
def test_runtime_placement_preserves_widgets_widths_and_button(source, destination, visible, qt_application, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QPushButton
    from pygpt_net.ui.layout.sidebar import pane_order
    from pygpt_net.ui import UI

    root = QWidget()
    root.resize(1400, 800)
    splitter = QSplitter(Qt.Horizontal, root)
    central_layout = QHBoxLayout(root)
    central_layout.setContentsMargins(0, 0, 0, 0)
    central_layout.addWidget(splitter)
    parts = {name: QWidget() for name in ('ctx', 'toolbox', 'chat')}
    parts['toolbox'].setMinimumWidth(200)
    for name in pane_order(source):
        splitter.addWidget(parts[name])
    if not visible:
        parts['toolbox'].hide()
    root.show()
    for index, name in enumerate(pane_order(source)):
        splitter.setStretchFactor(index, int(name == 'chat'))
    splitter.setSizes([{'ctx': 240, 'toolbox': 260 if visible else 0, 'chat': 780}[name]
                       for name in pane_order(source)])
    parts['toolbar'] = QWidget(root)
    layout = QVBoxLayout(parts['toolbar'])
    layout.addStretch()
    button = QPushButton(parts['toolbar'])
    button.setCheckable(True)
    button.setChecked(visible)
    parts['toolbar'].layout().addWidget(button)
    values = {'layout.toolbox.placement': destination}
    config = SimpleNamespace(
        get=lambda key, default=None: values.get(key, default),
        set=lambda key, value: values.__setitem__(key, value), save=MagicMock(),
    )
    ui = SimpleNamespace(parts=parts, nodes={'toolbar.toolbox': button}, splitters={'main': splitter})
    window = SimpleNamespace(core=SimpleNamespace(config=config), ui=ui)
    ui.window = window
    from pygpt_net.ui.toolbar import RightToolboxButtonHost
    parts['toolbar.right'] = RightToolboxButtonHost(window, root)
    ui.update_toolbox_button = lambda: UI.update_toolbox_button(ui)
    controller = Toolbar(window)
    controller._toolbox_visible = visible
    before = {name: splitter.sizes()[splitter.indexOf(parts[name])] for name in ('ctx', 'toolbox', 'chat')}
    controller.apply_toolbox_placement()
    assert [splitter.widget(i) for i in range(3)] == [parts[name] for name in pane_order(destination)]
    after = {name: splitter.sizes()[splitter.indexOf(parts[name])] for name in before}
    assert after == before
    assert parts['toolbox'].isHidden() is (not visible)
    assert button.parentWidget() is parts['toolbar.right' if destination == 'right' else 'toolbar']
    if destination == 'right':
        host = parts['toolbar.right']
        assert host.y() + host.height() + host.BOTTOM_MARGIN == root.height()
        if visible:
            toolbox = parts['toolbox']
            assert toolbox.x() + toolbox.width() == splitter.width()
            assert splitter.x() + splitter.width() == root.width()
    assert button.isChecked() is visible
    assert parts['toolbar.right'].isHidden() is (destination != 'right')
    if not visible:
        monkeypatch.setattr('pygpt_net.controller.toolbar.QVariantAnimation',
                            lambda parent: MagicMock())
        controller.toggle_toolbox()
        tick = controller._animation.valueChanged.connect.call_args.args[0]
        old_x = parts['toolbar.right'].x()
        tick(80)
        if destination == 'right':
            assert parts['toolbar.right'].x() < old_x
            chat = parts['chat']
            host = parts['toolbar.right']
            assert host.x() + host.width() + host.EDGE_MARGIN == chat.x() + chat.width()
        assert splitter.sizes()[splitter.indexOf(parts['toolbox'])] == 80
        assert splitter.sizes()[splitter.indexOf(parts['ctx'])] == before['ctx']
        tick(260)
        controller._finish_toolbox_animation(True)
        assert parts['toolbox'].minimumWidth() == 200
    # Startup restores the preference without running an animation or saving.
    values['layout.toolbox.width'] = 280
    saves = config.save.call_count
    for expanded in (True, False):
        values['layout.toolbox.expanded'] = expanded
        controller.restore_toolbox_state()
        restored = splitter.sizes()
        assert restored[splitter.indexOf(parts['toolbox'])] == (280 if expanded else 0)
        assert restored[splitter.indexOf(parts['ctx'])] == before['ctx']
        assert parts['toolbox'].isHidden() is (not expanded)
        assert button.isChecked() is expanded
        assert controller._toolbox_visible is expanded
    assert config.save.call_count == saves
    root.close()
