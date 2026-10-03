from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt, QTimer, QEventLoop, QPoint
from PySide6.QtWidgets import QMainWindow, QSplitter, QCheckBox, QWidget

from pygpt_net.controller.tabs.split import TabSplit
from pygpt_net.ui.widget.tabs.output import OutputTabs


def wait_animation():
    loop = QEventLoop()
    QTimer.singleShot(250, loop.quit)
    loop.exec()


def test_split_controls_keep_right_corner_and_follow_visible_column(qapp, monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.tabs.output.trans', lambda key: key)
    window = QMainWindow()
    values = {'layout.split': False}
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: values.get(key, default)
    config.set.side_effect = lambda key, value: values.__setitem__(key, value)
    window.core = SimpleNamespace(config=config)
    window.ui = SimpleNamespace(nodes={}, splitters={})
    controller = TabSplit()
    controller.window = window
    for name in ('update_current', '_sync_chat_input_width',
                 '_schedule_revealed_split_chat_restore', 'on_column_changed',
                 'set_current_column_idx', 'on_tab_changed'):
        setattr(controller, name, MagicMock())
    window.controller = SimpleNamespace(tabs=controller)
    box = QCheckBox()
    window.ui.nodes['layout.split'] = SimpleNamespace(box=box)
    left = OutputTabs(window, SimpleNamespace(get_idx=lambda: 0))
    right = OutputTabs(window, SimpleNamespace(get_idx=lambda: 1))
    for tabs in (left, right):
        tabs.addTab(QWidget(), 'Chat')
    splitter = QSplitter(Qt.Horizontal)
    splitter.addWidget(left)
    splitter.addWidget(right)
    window.ui.splitters['columns'] = splitter
    window.setCentralWidget(splitter)
    window.resize(1000, 600)
    window.show()
    splitter.setSizes([1, 0])
    controller.sync_split_buttons()
    qapp.processEvents()
    assert right.isHidden()
    assert not splitter.handle(1).isVisible()
    original_button_x = left.split_button.mapTo(window, QPoint(0, 0)).x()
    assert left.split_button.isVisible()
    assert right.split_button.isHidden()
    # Tool auto-open enters through the same API as the tab-bar button.
    controller.enable_split_screen(update_switch=True)
    animation = controller._split_animation
    controller.enable_split_screen(update_switch=True)
    assert controller._split_animation is animation
    from pygpt_net.core.types.animation import PANEL_ANIMATION_EASING, PANEL_ANIMATION_DURATION_MS
    assert animation.easingCurve().type() == PANEL_ANIMATION_EASING
    assert animation.duration() == PANEL_ANIMATION_DURATION_MS
    wait_animation()
    assert values['layout.split']
    assert splitter.handle(1).isVisible()
    assert abs(right.split_button.mapTo(window, QPoint(0, 0)).x() - original_button_x) <= 1
    assert right.split_button.isVisible()
    assert left.split_button.isHidden()
    assert abs(splitter.sizes()[0] - splitter.sizes()[1]) < 10
    for corner in (Qt.TopRightCorner, None, Qt.TopLeftCorner, Qt.TopRightCorner):
        right.place_add_button(right.tabBar().corner_button, corner)
        assert right.cornerWidget(Qt.TopRightCorner) is right.corner_controls
        assert right.split_button.parentWidget() is right.corner_controls
    right.split_button.click()
    wait_animation()
    assert not values['layout.split']
    assert not box.isChecked()
    assert splitter.sizes()[1] == 0
    assert right.isHidden()
    assert not splitter.handle(1).isVisible()
    assert left.split_button.isVisible()
    assert right.split_button.isHidden()
    window.close()
