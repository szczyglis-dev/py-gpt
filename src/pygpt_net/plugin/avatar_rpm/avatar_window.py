# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWidgets import QWidget, QVBoxLayout
from pathlib import Path


class AvatarWindow(QWidget):
    """Floating window with 3D Ready Player Me avatar"""

    emotion_changed = Signal(str)
    speaking_changed = Signal(bool)

    def __init__(self, parent=None, plugin=None):
        super().__init__(parent)
        self.plugin = plugin

        flags = Qt.Window
        if plugin.get_option_value("always_on_top"):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowTitle("PyGPT Avatar")
        self.setWindowFlags(flags)

        w = plugin.get_option_value("window_width")
        h = plugin.get_option_value("window_height")
        self.resize(w, h)
        self.setMinimumSize(200, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)
        layout.addWidget(self.web_view)

        self.channel = QWebChannel()
        self.channel.registerObject("backend", self)
        self.web_view.page().setWebChannel(self.channel)

        html_path = Path(__file__).parent / "assets" / "avatar_viewer.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))

        if plugin.get_option_value("auto_hide"):
            self.idle_timer = QTimer()
            self.idle_timer.timeout.connect(self.hide)
            self.idle_timer.setInterval(30000)
            self.idle_timer.start()

        self.current_emotion = "neutral"
        self.is_speaking = False

    def load_avatar(self):
        avatar_url = self.plugin.get_option_value("avatar_url")
        if not avatar_url:
            avatar_url = str(Path(__file__).parent / "assets" / "default_avatar.glb")
        js = f"if(typeof avatarManager!=='undefined'){{avatarManager.loadAvatar('{avatar_url}');}}"
        self.web_view.page().runJavaScript(js)

    def set_emotion(self, emotion: str):
        if emotion == self.current_emotion:
            return
        self.current_emotion = emotion
        self.emotion_changed.emit(emotion)
        js = f"if(typeof avatarManager!=='undefined'){{avatarManager.setEmotion('{emotion}');}}"
        self.web_view.page().runJavaScript(js)

    def speak(self, is_speaking: bool, volume: float = 0.5):
        self.is_speaking = is_speaking
        self.speaking_changed.emit(is_speaking)
        js = f"if(typeof avatarManager!=='undefined'){{avatarManager.speak({str(is_speaking).lower()},{volume});}}"
        self.web_view.page().runJavaScript(js)

    def reset_idle_timer(self):
        if hasattr(self, "idle_timer"):
            self.idle_timer.stop()
            self.show()
            self.idle_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(800, self.load_avatar)
