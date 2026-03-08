# -*- coding: utf-8 -*-
"""
Plugin: Avatar Ready Player Me
Description: 3D interactive avatar with Ready Player Me + Three.js
Author: Community Enhanced
Version: 1.0.0
"""
from pygpt_net.plugin.base import BasePlugin
from .avatar_window import AvatarWindow
from .lip_sync import LipSyncController
from .emotions import EmotionDetector


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "avatar_rpm"
        self.name = "Avatar Ready Player Me"
        self.description = "3D interactive avatar with Ready Player Me"
        self.order = 100
        self.use_locale = True

        self.avatar_window = None
        self.lip_sync = None
        self.emotion_detector = None

    def init_options(self):
        self.add_option("enabled", type="bool", value=False,
                        label="Enable Avatar Window",
                        description="Show 3D avatar floating window")
        self.add_option("avatar_url", type="text", value="",
                        label="Ready Player Me Avatar URL",
                        description="e.g. https://models.readyplayer.me/xxxxx.glb")
        self.add_option("window_width", type="int", value=300,
                        label="Window Width (px)", min=200, max=800)
        self.add_option("window_height", type="int", value=450,
                        label="Window Height (px)", min=300, max=1000)
        self.add_option("always_on_top", type="bool", value=True,
                        label="Always on top")
        self.add_option("auto_hide", type="bool", value=False,
                        label="Auto-hide when idle (30s)")
        self.add_option("lip_sync", type="bool", value=True,
                        label="Enable lip-sync with audio output")
        self.add_option("emotion_detection", type="bool", value=True,
                        label="Enable emotion detection")
        self.add_option("idle_animations", type="bool", value=True,
                        label="Enable idle animations (breathing, blinking)")
        self.add_option("background_color", type="text", value="#1a1a2e",
                        label="Background color (hex)")

    def setup(self):
        return self.options

    def attach(self, window):
        self.window = window
        if self.get_option_value("enabled"):
            self.create_avatar_window()

    def create_avatar_window(self):
        if self.avatar_window is None:
            self.avatar_window = AvatarWindow(parent=self.window, plugin=self)
            if self.get_option_value("lip_sync"):
                self.lip_sync = LipSyncController(self.avatar_window)
            if self.get_option_value("emotion_detection"):
                self.emotion_detector = EmotionDetector()
            self.avatar_window.show()

    def on_audio_output_start(self, text: str):
        if not self.avatar_window:
            return
        if self.emotion_detector:
            emotion = self.emotion_detector.detect(text)
            self.avatar_window.set_emotion(emotion)
        if self.lip_sync:
            self.lip_sync.start(text)

    def on_audio_output_chunk(self, audio_data: bytes, volume: float):
        if self.lip_sync:
            self.lip_sync.update(audio_data, volume)

    def on_audio_output_end(self):
        if self.lip_sync:
            self.lip_sync.stop()
        if self.avatar_window:
            self.avatar_window.set_emotion("neutral")

    def on_ctx_begin(self, ctx):
        if self.avatar_window:
            self.avatar_window.reset_idle_timer()

    def on_enable(self):
        if not self.avatar_window:
            self.create_avatar_window()

    def on_disable(self):
        if self.avatar_window:
            self.avatar_window.close()
            self.avatar_window = None
