#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 15:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QIcon, QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                               QFileDialog, QSlider, QLabel, QStyle, QSizePolicy, QMenu, QMessageBox)

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans

import pygpt_net.icons_rc

class VideoPlayerWidget(QWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self.player = QMediaPlayer(window)
        self.loaded = False
        self.path = None
        self.stopped = False
        self.seeking = False

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(200)
        self.update_timer.timeout.connect(self.update_ui)
        self.autoplay_timer = QTimer(self)
        self.autoplay_timer.setInterval(1000)
        self.autoplay_timer.setSingleShot(True)
        self.autoplay_timer.timeout.connect(self.after_loaded)

        self.audio = QAudioOutput()
        self.video = QVideoWidget(window)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setMinimumSize(640, 480)

        self.btn_play_pause = QPushButton()
        self.btn_play_pause.setEnabled(False)

        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
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

        # layout
        layout_controls = QHBoxLayout()
        layout_controls.addWidget(self.btn_open)
        layout_controls.addWidget(self.btn_play_pause)
        layout_controls.addWidget(self.btn_stop)

        layout_slider = QHBoxLayout()
        layout_slider.addWidget(self.label_time)
        layout_slider.addWidget(self.slider)
        layout_slider.addWidget(self.label_duration)

        layout = QVBoxLayout()
        layout.addWidget(self.video)
        layout.addLayout(layout_slider)
        layout.addLayout(layout_controls)
        layout.addLayout(layout_bottom)

        self.setLayout(layout)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        self.update_play_pause_icon()
        self.bind_signals()

    def bind_signals(self):
        """Bind signals"""
        self.btn_open.clicked.connect(self.open_file)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_stop.clicked.connect(self.stop_video)
        self.btn_mute.toggled.connect(self.set_muted)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self.media_status_changed)
        self.video.mousePressEvent = self.video_widget_clicked

        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.volume_slider.valueChanged.connect(self.adjust_volume)
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.seeking = False

    def update(self):
        """Update player"""
        self.update_mute_icon()
        self.update_volume_slider()
        self.update_label_path()

    def open_file(self):
        """Open file"""
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
        self.player.setSource(QUrl.fromLocalFile(path))
        self.set_path(path)
        self.enable()
        self.autoplay_timer.start()
        self.update()
        self.window.tools.get("player").store_path(path)  # save

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
            self.update_audio()
            self.player.play()

    def stop_video(self):
        """Stop video"""
        if self.player.source():
            self.player.stop()
        self.stopped = True
        self.slider.setValue(0)
        self.label_time.setText(self.format_time(0))
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.update_timer.stop()

    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.play_video()

        self.on_playback_state_changed()

    def reset(self):
        """Reset player to default state"""
        if self.player.source():
            self.player.stop()
            self.player.setSource(QUrl())
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.update_timer.stop()
        self.slider.setValue(0)
        self.seeking = False
        self.loaded = False

    def reset_player(self):
        """Reset player to default state"""
        if self.player is not None:
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.stop()
            self.player.setSource(QUrl())

    def on_context_menu(self, point):
        """
        Context menu event

        :param point: point
        """
        if not self.path or not self.player.source():
            return

        # TODO: implement grab screenshot
        """
        use_actions = []
        action_as_attachment = QAction(
            QIcon(":/icons/attachment.svg"),
            trans('action.use.attachment'),
            self,
        )
        action_as_attachment.triggered.connect(
            lambda: self.use_as_attachment(),
        )
        action_as_image = QAction(
            QIcon(":/icons/image.svg"),
            trans('action.use.image'),
            self,
        )
        action_as_image.triggered.connect(
            lambda: self.use_as_image(),
        )
        use_actions.append(action_as_image)
        use_actions.append(action_as_attachment)

        # use by type
        if use_actions:
            # use menu
            use_menu = QMenu(trans('action.use'), self)
            for action in use_actions:
                use_menu.addAction(action)
            context_menu.addMenu(use_menu)
        """
        context_menu = QMenu(self)
        save_as_action = QAction(QIcon(":/icons/save.svg"), trans("action.save_as"), self)
        save_as_action.triggered.connect(
            lambda: self.window.tools.get("player").save_as_file()
        )
        # full_screen_action = QAction('Fullscreen', self)
        # full_screen_action.triggered.connect(self.toggle_fullscreen)
        context_menu.addAction(save_as_action)

        # context_menu.addAction(full_screen_action)
        context_menu.exec(self.mapToGlobal(point))

    def use_as_attachment(self):
        """Use as attachment"""
        # TODO: implement grab screenshot
        path = self.window.tools.get("player").grab_frame()
        self.window.controller.files.use_attachment(path)

    def use_as_image(self):
        """Use as image"""
        # TODO: implement grab screenshot
        path = self.window.tools.get("player").grab_frame()
        self.window.controller.painter.open_external(path)

    def adjust_volume(self, value):
        """
        Adjust volume

        :param value: volume value
        """
        self.window.core.config.set("video.player.volume", value)  # save
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
            if not self.player.source():
                self.reset()
                self.player.setSource(QUrl.fromLocalFile(self.path))
            self.enable()
            self.update()
        self.window.ui.dialog["video_player"].setWindowTitle(os.path.basename(self.path))

    def on_close(self):
        """Stop video"""
        self.reset()

    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        # TODO: implement fullscreen
        if self.window.ui.dialog['video_player'].isFullScreen():
            self.window.ui.dialog['video_player'].showNormal()
        else:
            self.window.ui.dialog['video_player'].showFullScreen()

    def media_status_changed(self, status):
        """
        Media status changed

        :param status: status
        """
        if status == QMediaPlayer.LoadedMedia:
            self.loaded = True
            self.force_resize()
        elif status == QMediaPlayer.InvalidMedia:
            self.loaded = False
            self.window.ui.dialogs.alert("Failed to load media file, missing video codec?")

    def after_loaded(self):
        """Start playback after loaded"""
        if self.player.mediaStatus() == QMediaPlayer.LoadedMedia:
            self.loaded = True
            if self.player.playbackState() != QMediaPlayer.PlayingState:
                self.toggle_play_pause()
                self.force_resize()

    def force_resize(self):
        """Force resize fix"""
        # fix for video not showing after re-opening the dialog
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
        self.audio.setMuted(state)
        self.window.core.config.set("video.player.volume.mute", state)  # save

    def set_position(self, position):
        """
        Set position

        :param position: position
        """
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()

        self.player.positionChanged.connect(self.on_position_set)
        self.player.setPosition(position)

    def on_slider_pressed(self):
        """Slider pressed"""
        self.seeking = True
        self.player.pause()

    def on_slider_released(self):
        """Slider released"""
        if self.seeking:
            self.player.setPosition(self.slider.value())
            self.update_audio()
            self.player.play()
            self.seeking = False

    def position_changed(self, position):
        """
        Position changed

        :param position: position
        """
        if not self.seeking:
            self.slider.setValue(position)
            self.label_time.setText(self.format_time(position))

    def on_position_set(self, position):
        """
        On position set

        :param position: position
        """
        if self.seeking:
            self.player.positionChanged.disconnect(self.on_position_set)
            if self.player.playbackState() == QMediaPlayer.PausedState:
                QTimer.singleShot(100, self.player.play)
            self.seeking = False

    def update_label_path(self):
        """Update label path"""
        if self.path:
            self.label_path.setText(os.path.basename(self.path))
        else:
            self.label_path.setText("")

    def update_play_pause_icon(self):
        """Update play/pause icon"""
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.update_timer.start()
        else:
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.update_timer.stop()

    def update_audio(self):
        """Re-assign audio"""
        self.player.setAudioOutput(None)  # audio respawn fix
        self.player.setAudioOutput(self.audio)

    def update_mute_icon(self):
        """Update mute icon"""
        self.btn_mute.setChecked(self.audio.isMuted())

    def update_volume_slider(self):
        """Update volume slider"""
        self.volume_slider.setValue(self.audio.volume() * 100)

    def update_ui(self):
        """Update UI"""
        # sync slider with the video time
        self.position_changed(self.player.position())

    def format_time(self, ms):
        """
        Format time

        :param ms: milliseconds
        """
        # convert ms to H:M:S format
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000) % 60
        hours = (ms // 3600000)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)