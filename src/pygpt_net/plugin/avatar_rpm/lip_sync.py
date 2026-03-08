# -*- coding: utf-8 -*-
import numpy as np
from PySide6.QtCore import QObject, QTimer


class LipSyncController(QObject):
    """Audio-reactive lip-sync controller"""

    def __init__(self, avatar_window):
        super().__init__()
        self.avatar_window = avatar_window
        self.is_active = False
        self.current_volume = 0.0

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_mouth)
        self.update_timer.setInterval(50)  # 20 FPS

    def start(self, text: str):
        self.is_active = True
        self.avatar_window.speak(True, 0.5)
        self.update_timer.start()

    def update(self, audio_data: bytes, volume: float):
        self.current_volume = min(1.0, max(0.0, volume))

    def stop(self):
        self.is_active = False
        self.update_timer.stop()
        self.avatar_window.speak(False, 0.0)

    def _update_mouth(self):
        if not self.is_active:
            return
        noise = np.random.uniform(-0.1, 0.1)
        volume = max(0.0, min(1.0, self.current_volume + noise))
        self.avatar_window.speak(True, volume)
