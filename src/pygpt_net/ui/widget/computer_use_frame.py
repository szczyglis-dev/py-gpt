"""Click-through desktop borders shown while computer control is active."""
from PySide6.QtCore import Qt, QObject, QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QApplication, QWidget


class DesktopBorder(QWidget):
    BORDER_WIDTH = 4

    def __init__(self, screen, edge):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint |
                         Qt.WindowStaysOnTopHint | Qt.WindowTransparentForInput |
                         Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self._screen = screen
        self.edge = edge
        self.update_geometry(screen.geometry())
        screen.geometryChanged.connect(self.update_geometry)

    def update_geometry(self, rect):
        width = self.BORDER_WIDTH
        if self.edge == 'top':
            geometry = QRect(rect.x(), rect.y(), rect.width(), width)
        elif self.edge == 'bottom':
            geometry = QRect(rect.x(), rect.bottom() - width + 1, rect.width(), width)
        elif self.edge == 'left':
            geometry = QRect(rect.x(), rect.y() + width, width, max(0, rect.height() - 2 * width))
        else:
            geometry = QRect(rect.right() - width + 1, rect.y() + width, width, max(0, rect.height() - 2 * width))
        self.setGeometry(geometry)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#55ff70'))


class ComputerUseFrame(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.active = False
        self.borders = {}
        app = QApplication.instance()
        app.screenAdded.connect(self._add_screen)
        app.screenRemoved.connect(self._remove_screen)
        app.aboutToQuit.connect(self.hide)

    def _add_screen(self, screen):
        if self.active and screen not in self.borders:
            borders = [DesktopBorder(screen, edge) for edge in ('top', 'bottom', 'left', 'right')]
            self.borders[screen] = borders
            for border in borders:
                border.show()

    def _remove_screen(self, screen):
        for border in self.borders.pop(screen, []):
            border.close()
            border.deleteLater()

    def show(self):
        self.active = True
        for screen in QApplication.screens():
            self._add_screen(screen)

    def hide(self):
        self.active = False
        for screen in list(self.borders):
            self._remove_screen(screen)
