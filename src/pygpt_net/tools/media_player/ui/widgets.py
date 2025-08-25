#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.25 03:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                               QFileDialog, QSlider, QLabel, QStyle, QSizePolicy, QMenu, QMessageBox)

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans

class VideoPlayerWidget(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self.player = None
        self.audio = None
        self.video = None
        self.loaded = False
        self.path = None
        self.stopped = False
        self.seeking = False

        self._QMediaPlayer = None
        self._QAudioOutput = None
        self._QVideoWidget = None

        self._waiting_position_set = False
        self._last_position = -1

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(200)
        self.update_timer.timeout.connect(self.update_ui)
        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(1000)
        self.autoplay_timer.setSingleShot(True)
        self.autoplay_timer.timeout.connect(self.after_loaded)

        self._video_placeholder = QWidget(window)
        self._video_placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._video_placeholder.setMinimumSize(640, 480)

        self._icon_play = self.style().standardIcon(QStyle.SP_MediaPlay)
        self._icon_pause = self.style().standardIcon(QStyle.SP_MediaPause)
        self._icon_stop = self.style().standardIcon(QStyle.SP_MediaStop)

        self.btn_play_pause = QPushButton()
        self.btn_play_pause.setEnabled(False)

        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(self._icon_stop)
        self.btn_stop.setEnabled(False)

        self.btn_mute = QPushButton()
        self.btn_mute.setIcon(QIcon(':/icons/mute.svg'))
        self.btn_mute.setCheckable(True)

        self.btn_open = QPushButton(trans("action.video.open"))

        self.label_duration = QLabel()
        self.label_time = QLabel()
        self.label_path = HelpLabel("")
        self.label_path.setWordWrap(False)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setToolTip('Adjust volume')

        layout_volume = QHBoxLayout()
        layout_volume.addWidget(self.volume_slider)
        layout_volume.addWidget(self.btn_mute)

        layout_bottom = QHBoxLayout()
        layout_bottom.addWidget(self.label_path)
        layout_bottom.addStretch()
        layout_bottom.addLayout(layout_volume)

        layout_controls = QHBoxLayout()
        layout_controls.addWidget(self.btn_open)
        layout_controls.addWidget(self.btn_play_pause)
        layout_controls.addWidget(self.btn_stop)

        layout_slider = QHBoxLayout()
        layout_slider.addWidget(self.label_time)
        layout_slider.addWidget(self.slider)
        layout_slider.addWidget(self.label_duration)

        layout = QVBoxLayout()
        layout.addWidget(self._video_placeholder)
        layout.addLayout(layout_slider)
        layout.addLayout(layout_controls)
        layout.addLayout(layout_bottom)
        self._layout_main = layout

        self.setLayout(layout)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        self.update_play_pause_icon()
        self.bind_signals()

    def _ensure_multimedia(self):
        """Ensure multimedia components are loaded"""
        if self.player is not None:
            return
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtMultimediaWidgets import QVideoWidget
        self._QMediaPlayer = QMediaPlayer
        self._QAudioOutput = QAudioOutput
        self._QVideoWidget = QVideoWidget
        self.player = QMediaPlayer(self.window)
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget(self.window)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setMinimumSize(640, 480)
        idx = self._layout_main.indexOf(self._video_placeholder)
        if idx != -1:
            self._layout_main.removeWidget(self._video_placeholder)
            self._video_placeholder.setParent(None)
            self._layout_main.insertWidget(idx, self.video)
        else:
            self._layout_main.insertWidget(0, self.video)
        self.video.mousePressEvent = self.video_widget_clicked
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self.media_status_changed)
        self.update_mute_icon()
        self.update_volume_slider()
        self.adjust_volume(self.volume_slider.value())
        self.set_muted(self.btn_mute.isChecked())

    def bind_signals(self):
        """Bind signals to player controls"""
        self.btn_open.clicked.connect(self.open_file)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_stop.clicked.connect(self.stop_video)
        self.btn_mute.toggled.connect(self.set_muted)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.valueChanged.connect(self.on_slider_value_changed)
        self._video_placeholder.mousePressEvent = self.video_widget_clicked
        self.seeking = False

    def update(self):
        """Update player state"""
        self.update_mute_icon()
        self.update_volume_slider()
        self.update_label_path()

    def open_file(self):
        """Open video file dialog"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            trans("action.video.open"),
            "",
            "Video and Audio Files (*.mp4 *.avi *.mkv *.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma *.webm *.mkv "
            "*.flv *.mov *.wmv *.3gp *.m4v *.mpg);;All Files (*)"
        )
        if path:
            self.open(path)

    def open(self, path: str):
        """
        Open video

        :param path: video path
        """
        self.loaded = False
        self.stopped = False
        self.seeking = False
        self.reset()
        self._ensure_multimedia()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.set_path(path)
        self.enable()
        self.autoplay_timer.start()
        self.update()
        self.window.tools.get("player").store_path(path)

    def enable(self):
        """Enable player"""
        self.btn_play_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

    def play_video(self):
        """Play video"""
        self.stopped = False
        if not self.loaded and self.path:
            self.open(self.path)
        else:
            self._ensure_multimedia()
            self.update_audio()
            self.player.play()

    def stop_video(self):
        """Stop video"""
        if self.player and self.player.source():
            self.player.stop()
        self.stopped = True
        self.slider.setValue(0)
        self.label_time.setText(self.format_time(0))
        self.btn_play_pause.setIcon(self._icon_play)
        self.update_timer.stop()

    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.player and self._QMediaPlayer and self.player.playbackState() == self._QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.play_video()
        self.on_playback_state_changed()

    def reset(self):
        """Reset player to default state"""
        if self.player and self.player.source():
            self.player.stop()
            self.player.setSource(QUrl())
        self.btn_play_pause.setIcon(self._icon_play)
        self.update_timer.stop()
        self.slider.setValue(0)
        self.seeking = False
        self.loaded = False
        self._waiting_position_set = False
        self._last_position = -1

    def reset_player(self):
        """Reset player to default state"""
        if self.player is not None:
            if self._QMediaPlayer and self.player.playbackState() == self._QMediaPlayer.PlayingState:
                self.player.stop()
            self.player.setSource(QUrl())

    def on_context_menu(self, point):
        """
        Context menu event

        :param point: point
        """
        if not self.path or not (self.player and self.player.source()):
            return
        context_menu = QMenu(self)
        save_as_action = QAction(QIcon(":/icons/save.svg"), trans("action.save_as"), self)
        save_as_action.triggered.connect(
            lambda: self.window.tools.get("player").save_as_file()
        )
        context_menu.addAction(save_as_action)
        context_menu.exec(self.mapToGlobal(point))

    def use_as_attachment(self):
        """Use as attachment"""
        path = self.window.tools.get("player").grab_frame()
        self.window.controller.files.use_attachment(path)

    def use_as_image(self):
        """Use as image"""
        path = self.window.tools.get("player").grab_frame()
        self.window.controller.painter.open_external(path)

    def adjust_volume(self, value):
        """
        Adjust volume

        :param value: volume value
        """
        self.window.core.config.set("video.player.volume", value)
        if self.audio:
            volume = value / 100.0
            self.audio.setVolume(volume)

    def set_path(self, path: str):
        """
        Set path to video

        :param path: path
        """
        self.path = path
        self.update_label_path()
        if not self.loaded and self.path:
            if not self.player or not self.player.source():
                self._ensure_multimedia()
                self.reset()
                self.player.setSource(QUrl.fromLocalFile(self.path))
            self.enable()
            self.update()
        self.window.ui.dialog["video_player"].setWindowTitle(os.path.basename(self.path))

    def on_close(self):
        """Stop video"""
        self.reset()
        self.autoplay_timer.stop()

    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        if self.window.ui.dialog['video_player'].isFullScreen():
            self.window.ui.dialog['video_player'].showNormal()
        else:
            self.window.ui.dialog['video_player'].showFullScreen()

    def media_status_changed(self, status):
        """
        Media status changed

        :param status: status
        """
        if not self._QMediaPlayer:
            return
        if status == self._QMediaPlayer.LoadedMedia:
            self.loaded = True
            self.force_resize()
        elif status == self._QMediaPlayer.InvalidMedia:
            self.loaded = False
            self.window.ui.dialogs.alert("Failed to load media file, missing video codec?")

    def after_loaded(self):
        """Start playback after loaded"""
        if self.player and self._QMediaPlayer and self.player.mediaStatus() == self._QMediaPlayer.LoadedMedia:
            self.loaded = True
            if self.player.playbackState() != self._QMediaPlayer.PlayingState:
                self.toggle_play_pause()
                self.force_resize()

    def force_resize(self):
        """Force resize fix"""
        if not self.video:
            return
        self.video.hide()
        self.video.show()
        self.video.update()
        current_size = self.window.ui.dialog['video_player'].size()
        self.window.ui.dialog['video_player'].resize(current_size.width() + 10, current_size.height() + 10)
        self.window.ui.dialog['video_player'].resize(current_size)
        self.window.ui.dialog['video_player'].repaint()
        w = self.video.width() - 1
        h = self.video.height() - 1
        self.video.resize(w, h)

    def on_playback_state_changed(self):
        """Playback state changed"""
        self.update_play_pause_icon()

    def video_widget_clicked(self, event):
        """
        Video widget clicked

        :param event: event
        """
        if event.button() == Qt.LeftButton:
            if self.loaded:
                self.toggle_play_pause()
        elif event.button() == Qt.RightButton:
            pass

    def duration_changed(self, duration):
        """
        Duration changed

        :param duration: duration
        """
        self.slider.setRange(0, duration)
        self.label_duration.setText(self.format_time(duration))

    def set_muted(self, state: bool):
        """
        Set volume muted

        :param state: muted
        """
        if self.audio:
            self.audio.setMuted(state)
        self.window.core.config.set("video.player.volume.mute", state)

    def set_position(self, position):
        """
        Set position

        :param position: position
        """
        if not self.player:
            return
        if self._QMediaPlayer and self.player.playbackState() == self._QMediaPlayer.PlayingState:
            self.player.pause()
        self._waiting_position_set = True
        self.player.setPosition(position)

    def on_slider_pressed(self):
        """Slider pressed"""
        self.seeking = True
        self._waiting_position_set = False
        if self.player:
            self.player.pause()

    def on_slider_value_changed(self, value):
        """Slider value changed"""
        if self.seeking:
            self.label_time.setText(self.format_time(value))

    def on_slider_released(self):
        """Slider released"""
        if self.seeking:
            if self.player:
                self.player.setPosition(self.slider.value())
                self.update_audio()
                QTimer.singleShot(0, self.player.play)
            self.seeking = False

    def position_changed(self, position):
        """
        Position changed

        :param position: position
        """
        if self._waiting_position_set and self.player:
            self._waiting_position_set = False
            if self._QMediaPlayer and self.player.playbackState() == self._QMediaPlayer.PausedState:
                QTimer.singleShot(100, self.player.play)
        if not self.seeking:
            self._last_position = position
            self.slider.setValue(position)
            self.label_time.setText(self.format_time(position))

    def update_label_path(self):
        """Update label path"""
        if self.path:
            self.label_path.setText(os.path.basename(self.path))
        else:
            self.label_path.setText("")

    def update_play_pause_icon(self):
        """Update play/pause icon"""
        if self.player and self._QMediaPlayer and self.player.playbackState() == self._QMediaPlayer.PlayingState:
            self.btn_play_pause.setIcon(self._icon_pause)
            if not self.update_timer.isActive():
                self.update_timer.start()
        else:
            self.btn_play_pause.setIcon(self._icon_play)
            if self.update_timer.isActive():
                self.update_timer.stop()

    def update_audio(self):
        """Re-assign audio"""
        if self.player and self.audio:
            try:
                current = self.player.audioOutput()
            except Exception:
                current = None
            if current is not self.audio:
                self.player.setAudioOutput(self.audio)

    def update_mute_icon(self):
        """Update mute icon"""
        if self.audio:
            muted = self.audio.isMuted()
            if self.btn_mute.isChecked() != muted:
                block = self.btn_mute.blockSignals(True)
                self.btn_mute.setChecked(muted)
                self.btn_mute.blockSignals(block)

    def update_volume_slider(self):
        """Update volume slider"""
        if self.audio:
            v = int(self.audio.volume() * 100)
            if self.volume_slider.value() != v:
                block = self.volume_slider.blockSignals(True)
                self.volume_slider.setValue(v)
                self.volume_slider.blockSignals(block)

    def update_ui(self):
        """Update UI"""
        if self.player and not self.seeking:
            pos = self.player.position()
            if pos != self._last_position:
                self._last_position = pos
                self.slider.setValue(pos)
                self.label_time.setText(self.format_time(pos))

    def format_time(self, ms):
        """
        Format time

        :param ms: milliseconds
        """
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000) % 60
        hours = (ms // 3600000)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)