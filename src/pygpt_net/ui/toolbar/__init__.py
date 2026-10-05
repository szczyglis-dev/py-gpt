"""Persistent navigation toolbar, independent of collapsible side panes."""
from PySide6.QtCore import QEvent, QPoint, QSize, Slot
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
        self.add_button(layout, 'home', ':/icons/home.svg', trans('output.tab.chat'),
                        window.controller.toolbar.home)
        self._tool_buttons = {}
        window.tools.registered.connect(self.add_tool)
        for tool in window.tools.get_all().values():
            self.add_tool(tool)
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

    @Slot(object)
    def add_tool(self, tool):
        """Insert entries when a tool registers, including after UI construction."""
        layout = self.layout()
        for name, button in self._tool_buttons.get(tool.id, []):
            layout.removeWidget(button)
            self.window.ui.nodes.pop('toolbar.' + name, None)
            button.deleteLater()
        self._tool_buttons[tool.id] = []
        position = 1
        for tool_id, buttons in self._tool_buttons.items():
            if tool_id == tool.id:
                break
            position += len(buttons)
        for index, item in enumerate(tool.get_toolbar()):
            suffix = item.id or (str(index) if index else '')
            name = tool.id + ('.' + suffix if suffix else '')
            button = self.add_button(layout, name, item.icon, '', item.handler)
            layout.removeWidget(button)
            layout.insertWidget(position + index, button)
            tool.add_lang_mapping(button, item.title, setter='setToolTip')
            self._tool_buttons[tool.id].append((name, button))

    def add_button(self, layout, name, icon, title, handler):
        button = LabelButton(parent=self)
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(24, 24))
        button.setFixedSize(40, 40)
        button.setToolTip(title)
        button.clicked.connect(lambda checked=False: handler())
        self.window.ui.nodes['toolbar.' + name] = button
        layout.addWidget(button)
        return button

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.window.menuBar().palette().window())


class RightToolboxButtonHost(QWidget):
    """Floating toggle following the chat/toolbox boundary without taking space."""

    EDGE_MARGIN = 4
    BOTTOM_MARGIN = 24

    def __init__(self, window, parent):
        super().__init__(parent)
        self.window = window
        self.setObjectName('rightToolbar')
        self.setFixedSize(40, 40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (parent, window.ui.splitters['main'], window.ui.parts['chat']):
            widget.installEventFilter(self)

    def update_position(self):
        from pygpt_net.ui.layout.sidebar import placement
        if placement(self.window.core.config) != 'right':
            return
        chat = self.window.ui.parts['chat']
        boundary = chat.mapTo(self.parentWidget(), QPoint(chat.width(), 0)).x()
        self.move(max(0, boundary - self.width() - self.EDGE_MARGIN),
                  max(0, self.parentWidget().height() - self.height() - self.BOTTOM_MARGIN))
        self.raise_()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.LayoutRequest):
            self.update_position()
        return super().eventFilter(watched, event)
