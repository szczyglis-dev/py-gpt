"""Persistent navigation toolbar, independent of collapsible side panes."""
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pygpt_net.ui.widget.element.button import LabelButton
from pygpt_net.utils import trans


class LeftToolbar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setObjectName('leftToolbar')
        self.setFixedWidth(48)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(8)
        actions = (
            ('home', 'home.svg', 'output.tab.chat'),
            ('files', 'folder.svg', 'output.tab.files'),
            ('painter', 'brush.svg', 'output.tab.painter'),
        )
        for name, icon, tooltip in actions:
            button = LabelButton(parent=self)
            button.setIcon(QIcon(':/icons/' + icon))
            button.setIconSize(QSize(24, 24))
            button.setFixedSize(40, 40)
            button.setToolTip(trans(tooltip))
            button.clicked.connect(getattr(window.controller.toolbar, name))
            window.ui.nodes['toolbar.' + name] = button
            layout.addWidget(button)
        layout.addStretch()
        toolbox_button = LabelButton(parent=self)
        toolbox_button.setIcon(QIcon(':/icons/build.svg'))
        toolbox_button.setIconSize(QSize(24, 24))
        toolbox_button.setFixedSize(40, 40)
        toolbox_button.setCheckable(True)
        toolbox_button.setToolTip(trans('toolbar.toolbox'))
        toolbox_button.clicked.connect(window.controller.toolbar.toggle_toolbox)
        window.ui.nodes['toolbar.toolbox'] = toolbox_button
        layout.addWidget(toolbox_button)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.window.menuBar().palette().window())
